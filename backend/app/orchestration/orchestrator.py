"""
HMRA Central Orchestrator

Coordinating:
- Memory retrieval with scope access control
- Level 1 Slow Mind (Strategic Planning)
- Level 2 Fast Mind (Tactical Step Coordination)
- Level 3 Executor (Operational Tool Execution: Web Search, Calculator, Documents, Memory)
- 5 Specialized Agents (Researcher, Coder, Reviewer, Critic, Synthesizer)
- Conflict detection and resolution handling
- Controlled memory write-back & promotion
- Real-time agent status tracking & comprehensive execution tracing
"""

import re
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

from ..llm import LLMClient
from ..memory.store import MemoryManager
from ..reasoning.slow_mind import SlowMind
from ..reasoning.fast_mind import FastMind
from ..reasoning.executor import Executor
from ..agents import (
    ResearcherAgent,
    CoderAgent,
    ReviewerAgent,
    CriticAgent,
    SynthesizerAgent,
    AgentSystem
)
from .state import GLOBAL_STATE_TRACKER
from ..db import connect
from ..memory.write_policy import assess_durability, build_memory_content

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

TRIVIAL_QUERIES = re.compile(r'^(hi|hello|hey|greetings|thanks|thank you|good morning|good evening|who are you)\b', re.IGNORECASE)

class Orchestrator:
    def __init__(
        self,
        llm: LLMClient,
        memory: Optional[MemoryManager] = None,
        trace_fn: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
    ):
        self.llm = llm
        self.memory = memory or MemoryManager()
        self.trace_fn = trace_fn

        # Reasoning components
        self.slow_mind = SlowMind(llm)
        self.executor = Executor()
        self.fast_mind = FastMind(self.executor)

        # Specialized agents
        self.agents = AgentSystem(llm, self.memory, self._wrap_trace)

    def _wrap_trace(self, stage: str, actor: str, data: Dict[str, Any]):
        if self.trace_fn:
            self.trace_fn(stage, actor, data)

    def run(
        self,
        query: str,
        requester: str = 'orchestrator',
        execution_id: Optional[str] = None,
        use_memory: bool = True,
        use_web_search: bool = False
    ) -> Dict[str, Any]:
        """Executes full HMRA workflow with hierarchical reasoning and multi-agent coordination."""
        exec_id = execution_id or f"exec_{uuid.uuid4().hex[:12]}"
        start_time = now_iso()

        # Update orchestrator state
        GLOBAL_STATE_TRACKER.set_status('orchestrator', 'RUNNING', f"Processing: {query[:45]}")
        self._wrap_trace('start', 'orchestrator', {'execution_id': exec_id, 'query': query, 'use_web': use_web_search, 'use_memory': use_memory})

        # Save initial execution record in database
        try:
            with connect() as c:
                c.execute(
                    '''INSERT INTO executions(id, query, requester, started_at, status)
                       VALUES(?, ?, ?, ?, 'RUNNING')''',
                    (exec_id, query, requester, start_time)
                )
        except Exception:
            pass

        # -------------------------------------------------------------
        # 1. SCOPE-AWARE MEMORY RETRIEVAL
        # -------------------------------------------------------------
        retrieved_memories = []
        context = ""
        if use_memory:
            GLOBAL_STATE_TRACKER.set_status('executor', 'RUNNING', 'Retrieving memories')
            retrieved_memories = self.memory.retrieve(query, requester=requester)
            GLOBAL_STATE_TRACKER.set_status('executor', 'SUCCESS')
            self._wrap_trace('memory_retrieval', 'memory', {
                'count': len(retrieved_memories),
                'memories': retrieved_memories
            })
            context = self.memory.context(retrieved_memories)

        # -------------------------------------------------------------
        # 2. LEVEL 1: SLOW MIND (STRATEGIC PLANNING)
        # -------------------------------------------------------------
        GLOBAL_STATE_TRACKER.set_status('slow_mind', 'RUNNING', 'Developing strategic plan')
        strategic_plan = self.slow_mind.plan(
            query=query,
            retrieved_memory_context=context[:1000],
            web_search_enabled=use_web_search,
            trace_fn=self._wrap_trace
        )
        GLOBAL_STATE_TRACKER.set_status('slow_mind', 'SUCCESS')
        time.sleep(0.3)

        # -------------------------------------------------------------
        # 3. LEVEL 2: FAST MIND (TACTICAL ORGANIZATION)
        # -------------------------------------------------------------
        GLOBAL_STATE_TRACKER.set_status('fast_mind', 'RUNNING', 'Organizing tactical subgoals')
        tactical_steps = self.fast_mind.organize_tactical_steps(strategic_plan)
        self._wrap_trace('fast_mind_plan', 'fast_mind', {'tactical_steps': tactical_steps})

        # -------------------------------------------------------------
        # 4. LEVEL 3: EXECUTOR (TOOLS EXECUTION)
        # -------------------------------------------------------------
        tool_results = []
        GLOBAL_STATE_TRACKER.set_status('executor', 'RUNNING', 'Executing operational tools')

        # Web Search tool
        if use_web_search or 'web_search' in strategic_plan.required_tools:
            search_query = strategic_plan.objective or query
            search_res = self.executor.run_tool(
                'web_search',
                {'query': search_query, 'count': 5},
                execution_id=exec_id,
                trace_fn=self._wrap_trace
            )
            tool_results.append(search_res)

        # Math / Calculator tool
        math_match = re.search(r'\b(?:calculate|what is|compute)\s+([0-9+\-*/().\s^%]+)(?:\?|$)', query, re.I)
        if math_match or 'calculator' in strategic_plan.required_tools:
            expr = math_match.group(1).strip() if math_match else query
            calc_res = self.fast_mind.execute_with_retry(
                'calculator',
                {'expression': expr},
                execution_id=exec_id,
                trace_fn=self._wrap_trace
            )
            tool_results.append(calc_res)

        # Current Time tool
        if re.search(r'\b(?:current|local|what)?\s*(?:time|date|today)\b', query, re.I) or 'current_time' in strategic_plan.required_tools:
            time_res = self.executor.run_tool('current_time', {}, execution_id=exec_id, trace_fn=self._wrap_trace)
            tool_results.append(time_res)

        GLOBAL_STATE_TRACKER.set_status('executor', 'IDLE')
        time.sleep(0.3)

        # -------------------------------------------------------------
        # 5. SPECIALIZED AGENTS WORKFLOW (Minimal structured context)
        # -------------------------------------------------------------
        # Step A: Researcher Agent
        GLOBAL_STATE_TRACKER.set_status('researcher', 'RUNNING', 'Gathering empirical findings')
        search_hits = []
        for tr in tool_results:
            if tr.get('tool') == 'web_search' and isinstance(tr.get('result'), dict):
                search_hits.extend(tr['result'].get('results', []))

        researcher_msg = self.agents.researcher.conduct_research(
            query=query,
            context=context[:1200],
            search_results=search_hits,
            execution_id=exec_id,
            trace_fn=self._wrap_trace
        )
        researcher_out = researcher_msg.content
        GLOBAL_STATE_TRACKER.set_status('researcher', 'SUCCESS')
        time.sleep(0.3)

        # Step B: Coder Agent (Invoked when code, programming, or debugging is relevant)
        coder_out = ""
        is_code_relevant = 'coder' in strategic_plan.required_agents or any(
            k in query.lower() for k in ('code', 'python', 'java', 'sql', 'javascript', 'debug', 'script', 'function', 'class', 'algorithm')
        )
        if is_code_relevant:
            GLOBAL_STATE_TRACKER.set_status('coder', 'RUNNING', 'Synthesizing code implementation')
            coder_msg = self.agents.coder.implement_code(
                task=query,
                context=context[:800],
                extra=researcher_out[:500],
                execution_id=exec_id,
                trace_fn=self._wrap_trace
            )
            coder_out = coder_msg.content
            GLOBAL_STATE_TRACKER.set_status('coder', 'SUCCESS')
            time.sleep(0.3)

        # Step C: Reviewer Agent (Quality Gate)
        GLOBAL_STATE_TRACKER.set_status('reviewer', 'RUNNING', 'Validating outputs against requirements')
        combined_draft = f"RESEARCHER SUMMARY:\n{researcher_out[:450]}"
        if coder_out:
            combined_draft += f"\n\nCODER WORK:\n{coder_out[:450]}"
        reviewer_msg = self.agents.reviewer.review(
            task=query,
            context=context[:800],
            candidate_outputs=combined_draft,
            execution_id=exec_id,
            trace_fn=self._wrap_trace
        )
        reviewer_out = reviewer_msg.content
        GLOBAL_STATE_TRACKER.set_status('reviewer', 'SUCCESS')
        time.sleep(0.3)

        # Step D: Critic Agent (Skeptical Analysis & Contradiction Detection)
        GLOBAL_STATE_TRACKER.set_status('critic', 'RUNNING', 'Stress-testing claims and detecting contradictions')
        critic_msg = self.agents.critic.criticize(
            task=query,
            context=context[:600],
            upstream_outputs=f"{combined_draft}\n\nREVIEW:\n{reviewer_out[:300]}",
            execution_id=exec_id,
            trace_fn=self._wrap_trace
        )
        critic_out = critic_msg.content
        GLOBAL_STATE_TRACKER.set_status('critic', 'SUCCESS')
        time.sleep(0.3)

        # Step E: Synthesizer Agent (Final Output Integration)
        GLOBAL_STATE_TRACKER.set_status('synthesizer', 'RUNNING', 'Integrating final authoritative answer')
        all_agent_inputs = (
            f"OBJECTIVE:\n{strategic_plan.objective[:200]}\n\n"
            f"RESEARCH EVIDENCE:\n{researcher_out[:500]}\n\n"
        )
        if coder_out:
            all_agent_inputs += f"CODE IMPLEMENTATION:\n{coder_out[:500]}\n\n"
        all_agent_inputs += (
            f"REVIEWER VERDICT:\n{reviewer_out[:300]}\n\n"
            f"CRITIC OBJECTIONS:\n{critic_out[:300]}\n\n"
            f"TOOLS:\n{json.dumps([t.get('result') for t in tool_results])[:300]}"
        )

        synthesizer_msg = self.agents.synthesizer.synthesize(
            task=query,
            context=context[:800],
            all_agent_inputs=all_agent_inputs,
            execution_id=exec_id,
            trace_fn=self._wrap_trace
        )
        final_answer = synthesizer_msg.content

        # Graceful fallback if synthesizer encountered error
        if final_answer.startswith('[synthesizer] Error'):
            final_answer = f"{researcher_out}\n\n*Reviewer Notes:* {reviewer_out}"

        GLOBAL_STATE_TRACKER.set_status('synthesizer', 'SUCCESS')

        # -------------------------------------------------------------
        # 6. SELECTIVE MEMORY WRITE-BACK & PROMOTION DECISION
        # -------------------------------------------------------------
        writeback_mem = None
        promotion_decision = None

        # Selective durable-memory write-back. Most traces, tool results,
        # errors, calculations, and one-off answers remain history rather than
        # becoming long-term knowledge.
        durable, write_reason = assess_durability(query, final_answer)
        self._wrap_trace('memory_write_gate', 'memory', {
            'accepted': durable,
            'reason': write_reason
        })

        if durable and not TRIVIAL_QUERIES.match(query.strip()):
            GLOBAL_STATE_TRACKER.set_status('orchestrator', 'REVIEW', 'Evaluating durable memory write-back')

            # Always start at PRIVATE. Broader sharing requires an explicit
            # promotion request and reviewer gate; it is never automatic.
            owner = requester if requester not in ('orchestrator', 'system') else 'synthesizer'
            writeback_mem = self.memory.add(
                content=build_memory_content(query, final_answer),
                scope='PRIVATE',
                owner_agent=owner,
                source='durable_memory_extractor',
                confidence=0.75,
                importance=0.60,
                source_quality=0.75,
                metadata={
                    'execution_id': exec_id,
                    'query': query,
                    'write_gate': write_reason,
                    'requires_review': True
                }
            )

            # Mark the candidate explicitly for review instead of making it
            # active shared knowledge.
            from ..memory.lifecycle import transition_status
            transition_status(
                writeback_mem['id'],
                'PENDING_REVIEW',
                actor='memory_extractor',
                reason='Durable-memory candidate requires reviewer validation before sharing'
            )
            writeback_mem = self.memory.get(writeback_mem['id'])

            self._wrap_trace('memory_write_back', 'memory', {
                'memory_id': writeback_mem['id'],
                'scope': 'PRIVATE',
                'status': 'PENDING_REVIEW',
                'owner': owner,
                'reason': write_reason
            })

            # Create a formal promotion request only. Do NOT auto-promote.
            eligible, reason = self.memory.promotion_mgr.evaluate_eligibility(writeback_mem, 'TEAM')
            promotion_request = None
            if eligible:
                promotion_request = self.memory.promotion_mgr.request_promotion(
                    memory_id=writeback_mem['id'],
                    target_scope='TEAM',
                    requested_by='orchestrator',
                    reason='Durable-memory candidate awaiting reviewer validation'
                )

            promotion_decision = {
                'promoted': False,
                'pending_review': True,
                'eligible_for_review': eligible,
                'promotion_request': promotion_request,
                'memory_id': writeback_mem['id'],
                'target_scope': 'TEAM',
                'reason': reason if eligible else 'Candidate stored privately pending reviewer approval'
            }
            self._wrap_trace('memory_promotion_pending', 'reviewer', promotion_decision)

        # -------------------------------------------------------------
        # 7. FINALIZE EXECUTION
        # -------------------------------------------------------------
        end_time = now_iso()
        GLOBAL_STATE_TRACKER.reset_all_to_idle()
        self._wrap_trace('complete', 'orchestrator', {'execution_id': exec_id})

        # Update database execution record
        try:
            with connect() as c:
                c.execute(
                    '''UPDATE executions
                       SET status = 'SUCCESS', ended_at = ?, final_answer = ?, plan_json = ?
                       WHERE id = ?''',
                    (end_time, final_answer, json.dumps(strategic_plan.to_dict()), exec_id)
                )
        except Exception:
            pass

        return {
            'execution_id': exec_id,
            'query': query,
            'answer': final_answer,
            'retrieved_memories': retrieved_memories,
            'strategic_plan': strategic_plan.to_dict(),
            'slow_mind': strategic_plan.raw_plan,
            'agents': {
                'researcher': researcher_out,
                'coder': coder_out,
                'reviewer': reviewer_out,
                'critic': critic_out,
                'synthesizer': final_answer
            },
            'tool_results': tool_results,
            'writeback': writeback_mem,
            'promotion_decision': promotion_decision
        }
