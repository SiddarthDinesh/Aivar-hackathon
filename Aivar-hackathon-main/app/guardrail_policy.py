from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional local ML/text libs. Import inside functions so tests still run when packages
# are not installed; fall back to lightweight keyword heuristics.

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore


class PolicyValidationError(ValueError):
    """Raised when a provider policy tries to weaken a base policy."""


@dataclass
class Rule:
    id: str
    type: str
    scope: str
    action: str
    threshold: Optional[float] = None
    keywords: List[str] = field(default_factory=list)
    similarity_threshold: Optional[float] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Rule":
        return cls(
            id=str(payload["id"]),
            type=str(payload["type"]),
            scope=str(payload.get("scope", "output")),
            action=str(payload.get("action", "block")),
            threshold=float(payload["threshold"]) if payload.get("threshold") is not None else None,
            keywords=[str(item) for item in payload.get("keywords", [])],
            similarity_threshold=float(payload["similarity_threshold"]) if payload.get("similarity_threshold") is not None else None,
        )


@dataclass
class Policy:
    version: str = "1.0"
    rules: List[Rule] = field(default_factory=list)
    provider_overlays: Dict[str, List[Rule]] = field(default_factory=dict)

    @classmethod
    def from_rules(cls, rules: List[Dict[str, Any]], version: str = "1.0") -> "Policy":
        return cls(version=version, rules=[Rule.from_dict(rule) for rule in rules])

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Policy":
        rules = [Rule.from_dict(rule) for rule in payload.get("rules", [])]
        return cls(version=str(payload.get("version", "1.0")), rules=rules)

    def merged_rules(self, provider: Optional[str] = None) -> List[Rule]:
        if provider is None:
            return list(self.rules)
        provider_rules = self.provider_overlays.get(provider, [])
        merged: List[Rule] = []
        base_rules = {rule.id: rule for rule in self.rules}
        for rule in self.rules:
            overlay = next((candidate for candidate in provider_rules if candidate.id == rule.id), None)
            if overlay is None:
                merged.append(rule)
            else:
                merged.append(self._merge_rules(rule, overlay))
        for overlay in provider_rules:
            if overlay.id not in base_rules:
                merged.append(overlay)
        return merged

    def _merge_rules(self, base_rule: Rule, overlay_rule: Rule) -> Rule:
        if overlay_rule.type != base_rule.type:
            raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' changes the rule type")
        if overlay_rule.scope != base_rule.scope:
            raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' changes the scope")

        if base_rule.action == "block" and overlay_rule.action != "block":
            raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' weakens the base action")
        if base_rule.action == "redact" and overlay_rule.action == "allow":
            raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' weakens the base action")

        if base_rule.threshold is not None and overlay_rule.threshold is not None:
            if overlay_rule.threshold > base_rule.threshold:
                raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' weakens the base threshold")
        elif overlay_rule.threshold is not None and base_rule.threshold is None:
            raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' introduces a threshold not allowed by base policy")

        if base_rule.keywords and overlay_rule.keywords is not None:
            if not set(overlay_rule.keywords).issuperset(set(base_rule.keywords)):
                raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' removes or weakens base keywords")

        if base_rule.similarity_threshold is not None and overlay_rule.similarity_threshold is not None:
            if overlay_rule.similarity_threshold > base_rule.similarity_threshold:
                raise PolicyValidationError(f"Provider overlay for rule '{base_rule.id}' weakens the base similarity threshold")

        return Rule(
            id=base_rule.id,
            type=base_rule.type,
            scope=base_rule.scope,
            action=overlay_rule.action if overlay_rule.action else base_rule.action,
            threshold=overlay_rule.threshold if overlay_rule.threshold is not None else base_rule.threshold,
            keywords=list(dict.fromkeys(base_rule.keywords + overlay_rule.keywords)),
            similarity_threshold=overlay_rule.similarity_threshold if overlay_rule.similarity_threshold is not None else base_rule.similarity_threshold,
        )


def load_policy_from_yaml(path: str | Path, provider: Optional[str] = None) -> Policy:
    path = Path(path)
    payload = _parse_yaml_file(path)
    policy = Policy.from_dict(payload.get("base", payload))
    overlays_payload = payload.get("providers", {}) or {}
    policy.provider_overlays = {
        provider_name: [Rule.from_dict(rule) for rule in provider_payload.get("rules", [])]
        for provider_name, provider_payload in overlays_payload.items()
    }

    if provider and provider in policy.provider_overlays:
        provider_rules = policy.provider_overlays[provider]
        for rule in provider_rules:
            base_rule = next((candidate for candidate in policy.rules if candidate.id == rule.id), None)
            if base_rule is not None:
                policy._merge_rules(base_rule, rule)
    return policy


def evaluate_text(text: str, policy: Policy, scope: str = "output", provider: Optional[str] = None) -> Dict[str, Any]:
    rules = policy.merged_rules(provider=provider)
    processed_text = text
    redacted = False
    # Collect extra metadata from rules (e.g., toxicity score)
    extra: Dict[str, Any] = {}
    for rule in rules:
        if rule.scope != scope:
            continue
        if rule.type == "pii":
            result = _evaluate_pii(processed_text, rule)
            if not result["allowed"]:
                return result
            if result.get("action") == "redact" and result.get("redacted_text") != processed_text:
                processed_text = result["redacted_text"]
                redacted = True
            continue
        if rule.type == "toxicity":
            result = _evaluate_toxicity(processed_text, rule)
            # If blocked by toxicity, return immediately with metadata
            if not result["allowed"]:
                return result
            # Otherwise, carry forward score/threshold info for analytics
            extra["toxicity_score"] = result.get("score")
            extra["toxicity_threshold"] = result.get("threshold")
        if rule.type == "topic":
            result = _evaluate_topic(processed_text, rule)
            if not result["allowed"]:
                return result
    if redacted:
        return {
            "allowed": True,
            "action": "redact",
            "rule_id": "pii",
            "reason": "PII detected",
            "redacted_text": processed_text,
        }
    out = {
        "allowed": True,
        "action": "allow",
        "rule_id": None,
        "reason": "No policy violations detected",
        "redacted_text": processed_text,
    }
    out.update(extra)
    # Backwards-compatible keys expected by tests / analytics
    if "toxicity_score" in extra and "score" not in out:
        out["score"] = extra.get("toxicity_score")
    if "toxicity_threshold" in extra and "threshold" not in out:
        out["threshold"] = extra.get("toxicity_threshold")
    return out


def _evaluate_pii(text: str, rule: Rule) -> Dict[str, Any]:
    matches = []
    for pattern, replacement in [
        (_EMAIL_PATTERN, "[REDACTED_EMAIL]"),
        (_PHONE_PATTERN, "[REDACTED_PHONE]"),
        (_CARD_PATTERN, "[REDACTED_CREDIT_CARD]"),
    ]:
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), replacement))
    if not matches:
        return {"allowed": True, "action": "allow", "rule_id": rule.id, "reason": "No PII detected", "redacted_text": text}

    redacted_text = text
    for start, end, replacement in sorted(matches, reverse=True):
        redacted_text = redacted_text[:start] + replacement + redacted_text[end:]

    if rule.action == "block":
        return {"allowed": False, "action": "block", "rule_id": rule.id, "reason": "PII detected", "redacted_text": redacted_text}
    if rule.action == "redact":
        return {"allowed": True, "action": "redact", "rule_id": rule.id, "reason": "PII detected", "redacted_text": redacted_text}
    return {"allowed": True, "action": rule.action, "rule_id": rule.id, "reason": "PII detected", "redacted_text": redacted_text}


def _evaluate_toxicity(text: str, rule: Rule) -> Dict[str, Any]:
    score = _calculate_toxicity_score(text)
    threshold = rule.threshold if rule.threshold is not None else 0.8
    if score >= threshold:
        return {"allowed": False, "action": "block", "rule_id": rule.id, "reason": "Toxicity threshold exceeded", "score": score, "threshold": threshold}
    return {"allowed": True, "action": "allow", "rule_id": rule.id, "reason": "Toxicity below threshold", "score": score, "threshold": threshold}


def _evaluate_topic(text: str, rule: Rule) -> Dict[str, Any]:
    normalized = text.lower()
    keywords = [keyword.lower() for keyword in rule.keywords]
    matched_keywords = [keyword for keyword in keywords if keyword in normalized]
    # Keyword match short-circuit
    if matched_keywords:
        if rule.action == "block":
            return {"allowed": False, "action": "block", "rule_id": rule.id, "reason": "Restricted topic detected", "matched_keywords": matched_keywords}
        return {"allowed": True, "action": rule.action, "rule_id": rule.id, "reason": "Restricted topic detected", "matched_keywords": matched_keywords}

    # If no direct keyword match, try lightweight semantic similarity when configured.
    similarity_score = 0.0
    if rule.similarity_threshold is not None and rule.keywords:
        similarity_score = _semantic_similarity_score(text, rule.keywords)
        if similarity_score >= rule.similarity_threshold:
            if rule.action == "block":
                return {"allowed": False, "action": "block", "rule_id": rule.id, "reason": "Restricted topic detected (semantic match)", "similarity_score": similarity_score}
            return {"allowed": True, "action": rule.action, "rule_id": rule.id, "reason": "Restricted topic detected (semantic match)", "similarity_score": similarity_score}

    return {"allowed": True, "action": "allow", "rule_id": rule.id, "reason": "No restricted topic detected", "similarity_score": similarity_score}
    if rule.action == "block":
        return {"allowed": False, "action": "block", "rule_id": rule.id, "reason": "Restricted topic detected", "matched_keywords": matched_keywords}
    return {"allowed": True, "action": rule.action, "rule_id": rule.id, "reason": "Restricted topic detected", "matched_keywords": matched_keywords}


def _calculate_toxicity_score(text: str) -> float:
    # Try using a lightweight local classifier when available (profanity-check).
    try:
        # Try profanity-check first (provides a probability)
        heuristic_score = 0.0
        lowered = text.lower()
        strong_terms = ["idiot", "stupid", "moron", "damn", "bastard", "fool", "hate"]
        moderate_terms = ["crap", "shit", "sucks", "jerk", "annoying"]
        if any(term in lowered for term in strong_terms):
            heuristic_score = 0.91
        elif any(term in lowered for term in moderate_terms):
            heuristic_score = 0.75

        # Try profanity-check first (provides a probability)
        try:
            from profanity_check import predict_prob  # type: ignore

            prob = float(predict_prob([text])[0])
            prob = max(0.0, min(1.0, prob))
            # Combine model prob with heuristic: take the max to be conservative
            return max(prob, heuristic_score)
        except Exception:
            # Try a simpler pure-Python profanity detector if available
            try:
                from better_profanity import profanity as bp  # type: ignore

                # better_profanity only provides a boolean check; convert to 1.0/0.0
                bp_score = 1.0 if bp.contains_profanity(text) else 0.0
                return max(bp_score, heuristic_score)
            except Exception:
                # Fall through to keyword heuristic
                return heuristic_score
    except Exception:
        # Fallback keyword heuristic (keeps backward compatibility and test stability).
        lowered = text.lower()
        strong_terms = ["idiot", "stupid", "moron", "damn", "bastard", "fool", "hate"]
        moderate_terms = ["crap", "shit", "sucks", "jerk", "annoying"]
        if any(term in lowered for term in strong_terms):
            return 0.91
        if any(term in lowered for term in moderate_terms):
            return 0.75
        return 0.0


def _semantic_similarity_score(text: str, candidates: List[str]) -> float:
    """Compute a simple TF-IDF + cosine similarity score between text and candidate phrases.

    Returns the maximum similarity in [0.0, 1.0]. Falls back to 0.0 if sklearn is unavailable.
    """
    # Try sklearn's TF-IDF + cosine similarity when available for best quality.
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

        docs = list(candidates) + [text]
        vectorizer = TfidfVectorizer().fit(docs)
        vectors = vectorizer.transform(docs)
        text_vec = vectors[-1]
        candidate_vecs = vectors[:-1]
        sims = cosine_similarity(text_vec, candidate_vecs)[0]
        if len(sims) == 0:
            return 0.0
        max_sim = float(max(sims))
        return max(0.0, min(1.0, max_sim))
    except Exception:
        # Fall back to a simple bag-of-words cosine similarity implemented in pure Python
        try:
            from collections import Counter
            import math

            def vectorize(doc: str) -> Counter:
                tokens = [t for t in re.findall(r"\w+", doc.lower())]
                return Counter(tokens)

            text_vec = vectorize(text)
            best = 0.0
            for cand in candidates:
                cand_vec = vectorize(cand)
                # dot product
                common = set(text_vec.keys()) & set(cand_vec.keys())
                num = sum(text_vec[k] * cand_vec[k] for k in common)
                denom = math.sqrt(sum(v * v for v in text_vec.values())) * math.sqrt(sum(v * v for v in cand_vec.values()))
                sim = (num / denom) if denom > 0 else 0.0
                if sim > best:
                    best = sim
            return max(0.0, min(1.0, float(best)))
        except Exception:
            return 0.0


_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){12,19}\d\b")


def _parse_yaml_file(path: Path) -> Dict[str, Any]:
    if yaml is not None:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            if isinstance(data, dict):
                return data
    raise ValueError("YAML support is unavailable")
