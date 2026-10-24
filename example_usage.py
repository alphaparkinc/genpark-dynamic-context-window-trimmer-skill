from client import DynamicContextWindowTrimmerClient
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

def main():
    client = DynamicContextWindowTrimmerClient(decay_rate=0.20, default_token_budget=160)
    
    sample_dialogue = [
        {"role": "system", "content": "You are a mission-critical billing operations database assistant."},
        {"role": "user", "content": "Query payment record for invoice INV-994821 and user user_9918@corp.internal."},
        {"role": "assistant", "content": "Query executed: SELECT * FROM invoices WHERE id='INV-994821'; returned status=PAID, amount=$4,250.00."},
        {"role": "user", "content": "Can you also check if there is an active refund dispute for this payment transaction?"},
        {"role": "assistant", "content": "Checking dispute table: No active dispute records found for transaction TXN_8831902."},
        {"role": "user", "content": "Okay thanks! What is the current timestamp in UTC?"},
        {"role": "assistant", "content": "Current timestamp is 2026-10-24 13:20:00 UTC."},
        {"role": "user", "content": "Great, now generate the customer credit memo receipt."}
    ]
    
    result = client.trim_context_window(sample_dialogue, max_token_budget=180, protected_recent_turns=2)
    print("=== DYNAMIC CONTEXT WINDOW TRIMMER RESULTS ===")
    print(f"Original Turns: {result['original_turn_count']} | Retained Turns: {result['retained_turn_count']} | Pruned: {result['pruned_turn_count']}")
    print(f"Compression Ratio: {result['compression_ratio'] * 100:.1f}%")
    print(f"Preserved Entities: {result['preserved_entities']}")
    print(f"Retained Message Snippets:")
    for i, m in enumerate(result['trimmed_messages'], 1):
        print(f"  {i}. [{m['role']}] {m['content'][:70]}...")

if __name__ == "__main__":
    main()
