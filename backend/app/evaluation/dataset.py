"""
HMRA Benchmark Evaluation Dataset

Covers 14 empirical test categories specified in research design:
1. Simple question
2. Multi-step reasoning
3. Long conversation
4. Contradictory facts
5. Knowledge sharing
6. Private memory isolation
7. Team memory retrieval
8. Global memory retrieval
9. Document-based QA
10. Web-assisted research
11. Tool failure/recovery
12. Duplicate memory detection
13. Memory promotion
14. Memory consolidation
"""

from typing import List, Dict, Any

EVALUATION_DATASET: List[Dict[str, Any]] = [
    {
        'id': 'tc_01_simple_qa',
        'category': '1. Simple question',
        'query': 'What is the primary objective of the HMRA architecture?',
        'expected_keywords': ['hierarchical', 'memory', 'reasoning', 'agent'],
        'required_scope': 'GLOBAL',
        'target_agent': 'researcher'
    },
    {
        'id': 'tc_02_multistep_reasoning',
        'query': 'Calculate (45 * 12) + (180 / 4) and explain the steps.',
        'expected_keywords': ['585', 'multiply', 'divide', 'add'],
        'required_tools': ['calculator'],
        'target_agent': 'synthesizer'
    },
    {
        'id': 'tc_03_long_conversation',
        'query': 'Recall our discussion about project milestones and summarize the immediate deliverables.',
        'expected_keywords': ['deliverable', 'milestone', 'summary'],
        'required_scope': 'TEAM',
        'target_agent': 'synthesizer'
    },
    {
        'id': 'tc_04_contradictory_facts',
        'query': 'What is the approved project database engine according to conflicting records?',
        'expected_keywords': ['sqlite', 'conflict', 'database', 'uncertainty'],
        'test_conflict': True,
        'target_agent': 'critic'
    },
    {
        'id': 'tc_05_knowledge_sharing',
        'query': 'What shared architectural decisions have been verified for the engineering team?',
        'expected_keywords': ['team', 'architecture', 'decision'],
        'required_scope': 'TEAM',
        'target_agent': 'coder'
    },
    {
        'id': 'tc_06_private_memory_isolation',
        'query': 'Can the Coder access the Researcher secret unpromoted private observation?',
        'expected_keywords': ['private', 'access', 'denied', 'isolated', 'cannot'],
        'test_isolation': True,
        'target_agent': 'coder'
    },
    {
        'id': 'tc_07_team_memory_retrieval',
        'query': 'Retrieve the sprint tasks agreed upon by the backend development team.',
        'expected_keywords': ['sprint', 'task', 'backend'],
        'required_scope': 'TEAM',
        'target_agent': 'reviewer'
    },
    {
        'id': 'tc_08_global_memory_retrieval',
        'query': 'What are the global architectural standards enforced across the entire system?',
        'expected_keywords': ['standard', 'global', 'rule', 'constraint'],
        'required_scope': 'GLOBAL',
        'target_agent': 'reviewer'
    },
    {
        'id': 'tc_09_document_qa',
        'query': 'Based on the uploaded technical specification, what are the three reasoning levels?',
        'expected_keywords': ['slow mind', 'fast mind', 'executor'],
        'target_agent': 'researcher'
    },
    {
        'id': 'tc_10_web_assisted_research',
        'query': 'What are recent developments in hierarchical memory architectures for agents?',
        'expected_keywords': ['memory', 'agent', 'architecture', 'hierarchical'],
        'target_agent': 'researcher'
    },
    {
        'id': 'tc_11_tool_failure_recovery',
        'query': 'Calculate 100 / 0 and recover if an arithmetic error occurs.',
        'expected_keywords': ['division by zero', 'error', 'recover', 'undefined'],
        'target_agent': 'executor'
    },
    {
        'id': 'tc_12_duplicate_memory_detection',
        'query': 'Check if duplicate project facts are detected and merged.',
        'expected_keywords': ['duplicate', 'merge', 'consolidat'],
        'target_agent': 'reviewer'
    },
    {
        'id': 'tc_13_memory_promotion',
        'query': 'Verify the graduation of private knowledge into team knowledge.',
        'expected_keywords': ['promote', 'team', 'reviewer', 'approved'],
        'target_agent': 'reviewer'
    },
    {
        'id': 'tc_14_memory_consolidation',
        'query': 'Run memory consolidation and report the count of merged records and open conflicts.',
        'expected_keywords': ['consolidation', 'report', 'merged', 'conflicts'],
        'target_agent': 'synthesizer'
    }
]
