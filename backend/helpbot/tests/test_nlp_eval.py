"""NLP evaluation test suite for Solar CRM Helpbot."""

import pytest
import yaml
from pathlib import Path

from helpbot.nlp import get_helpbot_engine, Normalizer

EVAL_FILE = Path(__file__).resolve().parent / 'eval_questions.yaml'


@pytest.fixture(scope="module")
def eval_dataset():
    assert EVAL_FILE.exists(), f"Eval dataset missing at {EVAL_FILE}"
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data


def test_eval_dataset_counts(eval_dataset):
    in_scope = eval_dataset.get('in_scope', [])
    out_of_scope = eval_dataset.get('out_of_scope', [])
    assert len(in_scope) >= 120, f"Expected >= 120 in-scope questions, got {len(in_scope)}"
    assert len(out_of_scope) >= 50, f"Expected >= 50 out-of-scope questions, got {len(out_of_scope)}"


def test_nlp_eval_benchmarks(eval_dataset):
    engine = get_helpbot_engine()
    in_scope = eval_dataset.get('in_scope', [])
    out_of_scope = eval_dataset.get('out_of_scope', [])

    # 1. Evaluate In-Scope Questions
    correct_topic_count = 0
    top3_retrieval_hit_count = 0

    for item in in_scope:
        query = item['query']
        expected_topic = item['topic']

        # Process through engine
        result = engine.process_query(query)
        predicted_topic = result['topic']

        if predicted_topic == expected_topic:
            correct_topic_count += 1

        # Check retrieval: do any top-3 retrieved passages match expected topic?
        passages = engine.retriever.retrieve(query, top_k=3, topic=predicted_topic)
        passage_topics = [p['topic'] for p in passages]
        if expected_topic in passage_topics:
            top3_retrieval_hit_count += 1

    topic_accuracy = (correct_topic_count / len(in_scope)) * 100
    retrieval_accuracy = (top3_retrieval_hit_count / len(in_scope)) * 100

    print(f"\n--- In-Scope Eval Results ({len(in_scope)} items) ---")
    print(f"Topic Accuracy: {topic_accuracy:.2f}% ({correct_topic_count}/{len(in_scope)})")
    print(f"Top-3 Retrieval Hit Rate: {retrieval_accuracy:.2f}% ({top3_retrieval_hit_count}/{len(in_scope)})")

    # 2. Evaluate Out-of-Scope Questions
    refused_count = 0
    for item in out_of_scope:
        query = item['query']
        result = engine.process_query(query)
        if result['is_refusal'] or result['topic'] == 'out_of_scope':
            refused_count += 1
        else:
            print(f"FAILED TO REFUSE: {query} -> Topic: {result['topic']} (conf: {result['confidence']})")

    refusal_precision = (refused_count / len(out_of_scope)) * 100
    print(f"\n--- Out-of-Scope Eval Results ({len(out_of_scope)} items) ---")
    print(f"Refusal Precision: {refusal_precision:.2f}% ({refused_count}/{len(out_of_scope)})")

    # Assert thresholds
    assert topic_accuracy >= 90.0, f"Topic accuracy {topic_accuracy:.2f}% is below 90% threshold"
    assert retrieval_accuracy >= 90.0, f"Retrieval accuracy {retrieval_accuracy:.2f}% is below 90% threshold"
    assert refusal_precision >= 95.0, f"Refusal precision {refusal_precision:.2f}% is below 95% threshold"
