from .base import BaseAgent, AgentMessage
from .researcher import ResearcherAgent
from .coder import CoderAgent
from .reviewer import ReviewerAgent
from .critic import CriticAgent
from .synthesizer import SynthesizerAgent

class AgentSystem:
    """Unified container for all 5 specialized HMRA agents."""
    def __init__(self, llm, memory=None, trace=None):
        self.llm = llm
        self.memory = memory
        self.trace = trace
        self.researcher = ResearcherAgent(llm, memory)
        self.coder = CoderAgent(llm, memory)
        self.reviewer = ReviewerAgent(llm, memory)
        self.critic = CriticAgent(llm, memory)
        self.synthesizer = SynthesizerAgent(llm, memory)
        self._agents = {
            'researcher': self.researcher,
            'coder': self.coder,
            'reviewer': self.reviewer,
            'critic': self.critic,
            'synthesizer': self.synthesizer
        }

    def call(self, role: str, task: str, context: str = "", extra: str = "", execution_id: str = None) -> str:
        agent = self._agents.get(role)
        if not agent:
            raise ValueError(f"Unknown agent role: {role}. Available: {list(self._agents.keys())}")
        msg = agent.execute(task=task, context=context, extra=extra, execution_id=execution_id, trace_fn=self.trace)
        return msg.content

    def get_agent(self, role: str) -> BaseAgent:
        return self._agents[role]

__all__ = [
    'BaseAgent',
    'AgentMessage',
    'ResearcherAgent',
    'CoderAgent',
    'ReviewerAgent',
    'CriticAgent',
    'SynthesizerAgent',
    'AgentSystem',
]
