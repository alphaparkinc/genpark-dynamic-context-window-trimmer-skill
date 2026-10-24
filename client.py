import re, math, sys
sys.stdout.reconfigure(encoding='utf-8')

class DynamicContextWindowTrimmerClient:
    """
    Deterministic context window trimmer utilizing exponential recency decay,
    entity preservation, and salience budgeting to keep conversations within token limits.
    """
    def __init__(self, decay_rate=0.15, default_token_budget=1024):
        self.decay_rate = decay_rate
        self.default_token_budget = default_token_budget
        self.salient_keywords = {
            "error", "failed", "bug", "exception", "traceback", "status",
            "order_id", "user_id", "email", "api_key", "token", "query",
            "result", "schema", "database", "table", "constraint", "fix",
            "instruction", "system", "requirement", "total", "amount", "uuid"
        }
        self.entity_pattern = re.compile(
            r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|'
            r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|'
            r'https?://[^\s]+|'
            r'`[^`]+`|'
            r'\b[A-Z0-9_]{6,}\b)',
            re.IGNORECASE
        )

    def estimate_tokens(self, text):
        words = len(text.split())
        chars = len(text)
        return max(1, int(words * 1.25 + (chars / 15.0)))

    def extract_entities(self, text):
        matches = self.entity_pattern.findall(text)
        return list(dict.fromkeys(matches))[:10]

    def score_turn(self, turn_idx, total_turns, role, content):
        dist_from_end = total_turns - 1 - turn_idx
        recency_weight = math.exp(-self.decay_rate * dist_from_end)
        
        words = content.lower().split()
        kw_hits = sum(1 for w in words if w in self.salient_keywords)
        kw_density = kw_hits / max(1, len(words))
        
        entities = self.extract_entities(content)
        entity_score = min(2.0, len(entities) * 0.4)
        
        role_weight = 1.3 if role == "system" else (1.1 if role == "user" else 1.0)
        
        composite_score = recency_weight * (1.0 + kw_density * 2.5 + entity_score) * role_weight
        return round(composite_score, 4), entities

    def trim_context_window(self, messages, max_token_budget=None, protected_recent_turns=2, preserve_entities=True):
        budget = max_token_budget or self.default_token_budget
        total_turns = len(messages)
        if total_turns == 0:
            return {"status": "success", "trimmed_messages": [], "pruned_turn_count": 0, "compression_ratio": 0.0}

        annotated = []
        total_orig_tokens = 0
        all_preserved_entities = set()

        for idx, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            est_tokens = self.estimate_tokens(content)
            total_orig_tokens += est_tokens
            
            score, entities = self.score_turn(idx, total_turns, role, content)
            if preserve_entities:
                all_preserved_entities.update(entities)
            
            is_protected = (role == "system") or (idx >= total_turns - protected_recent_turns)
            annotated.append({
                "index": idx,
                "role": role,
                "content": content,
                "tokens": est_tokens,
                "score": score,
                "is_protected": is_protected,
                "entities": entities
            })

        kept_indices = set()
        consumed_tokens = 0

        for item in annotated:
            if item["is_protected"]:
                kept_indices.add(item["index"])
                consumed_tokens += item["tokens"]

        candidates = [item for item in annotated if not item["is_protected"]]
        candidates.sort(key=lambda x: (x["score"] / max(1, x["tokens"])), reverse=True)

        for c in candidates:
            if consumed_tokens + c["tokens"] <= budget:
                kept_indices.add(c["index"])
                consumed_tokens += c["tokens"]

        trimmed_messages = []
        last_kept = -1
        dropped_clusters = []

        for idx in range(total_turns):
            if idx in kept_indices:
                if last_kept != -1 and idx > last_kept + 1:
                    dropped_clusters.append((last_kept + 1, idx - 1))
                trimmed_messages.append({"role": messages[idx]["role"], "content": messages[idx]["content"]})
                last_kept = idx

        if dropped_clusters and preserve_entities:
            summary_notice = (
                f"[System: Pruned {sum(end - start + 1 for start, end in dropped_clusters)} older turns. "
                f"Retained key entities: {', '.join(sorted(list(all_preserved_entities))[:5])}]"
            )
            insert_pos = 1 if (trimmed_messages and trimmed_messages[0]["role"] == "system") else 0
            trimmed_messages.insert(insert_pos, {"role": "system", "content": summary_notice})
            consumed_tokens += self.estimate_tokens(summary_notice)

        compression = round(1.0 - (consumed_tokens / max(1, total_orig_tokens)), 4)
        return {
            "status": "success",
            "original_turn_count": total_turns,
            "retained_turn_count": len(trimmed_messages),
            "pruned_turn_count": total_turns - len(kept_indices),
            "original_token_estimate": total_orig_tokens,
            "retained_token_estimate": consumed_tokens,
            "compression_ratio": max(0.0, compression),
            "preserved_entities": sorted(list(all_preserved_entities))[:10],
            "trimmed_messages": trimmed_messages
        }
