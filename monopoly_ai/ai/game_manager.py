"""Game Manager that orchestrates AI decisions and maintains game history."""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from .openai_agent import OpenAIMonopolyAgent


@dataclass
class GameEvent:
    """Represents a game event."""
    turn: int
    player_id: int
    event_type: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "turn": self.turn,
            "player": self.player_id,
            "type": self.event_type,
            "details": self.details,
            "time": self.timestamp.isoformat()
        }


@dataclass
class ChatMessage:
    """Represents a chat message between AI players."""
    sender_id: int
    sender_name: str
    message: str
    turn: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender_name,
            "message": self.message,
            "turn": self.turn,
            "time": self.timestamp.isoformat()
        }


class MonopolyGameManager:
    """Manages the game flow and AI interactions."""
    
    def __init__(self, player_names: List[str], enable_chat: bool = True):
        self.player_names = player_names
        self.enable_chat = enable_chat
        self.current_turn = 0
        
        # Create AI agents for each player
        self.ai_agents: Dict[int, OpenAIMonopolyAgent] = {}
        for i, name in enumerate(player_names):
            self.ai_agents[i] = OpenAIMonopolyAgent(name, model="gpt-4.1-nano")
        
        # Game history
        self.game_events: List[GameEvent] = []
        self.chat_history: List[ChatMessage] = []
        self.decision_history: Dict[int, List[Dict]] = {i: [] for i in range(len(player_names))}
        
    def get_game_context(self, player_id: int, game) -> Dict:
        """Get comprehensive game context for AI decision making."""
        player = game.players[player_id]
        opponents = [p for p in game.players if p.id != player_id]
        
        # Get owned properties with details
        my_properties = []
        for prop_pos in player.properties:
            square = game.board[prop_pos]
            if hasattr(square, 'name'):
                prop_info = {
                    "name": square.name,
                    "position": prop_pos,
                    "price": square.price if hasattr(square, 'price') else 0,
                    "mortgaged": square.mortgaged if hasattr(square, 'mortgaged') else False,
                    "houses": square.houses if hasattr(square, 'houses') else 0,
                    "color": square.color.value if hasattr(square, 'color') and square.color else None
                }
                my_properties.append(prop_info)
        
        # Get opponent properties
        opponent_properties = []
        for opp in opponents:
            opp_props = []
            for prop_pos in opp.properties:
                square = game.board[prop_pos]
                if hasattr(square, 'name'):
                    opp_props.append({
                        "name": square.name,
                        "color": square.color.value if hasattr(square, 'color') and square.color else None,
                        "houses": square.houses if hasattr(square, 'houses') else 0
                    })
            opponent_properties.append({
                "player": opp.name,
                "cash": opp.cash,
                "properties": opp_props,
                "in_jail": opp.in_jail,
                "position": opp.position
            })
        
        # Get recent events
        recent_events = [e.to_dict() for e in self.game_events[-10:]]
        
        # Get recent chat
        recent_chat = [m.to_dict() for m in self.chat_history[-5:]] if self.enable_chat else []
        
        return {
            "turn": self.current_turn,
            "my_status": {
                "name": player.name,
                "cash": player.cash,
                "position": player.position,
                "in_jail": player.in_jail,
                "jail_turns": player.jail_turns,
                "properties": my_properties,
                "net_worth": player.cash + sum(p["price"] for p in my_properties if not p["mortgaged"])
            },
            "opponents": opponent_properties,
            "recent_events": recent_events,
            "recent_chat": recent_chat,
            "my_recent_decisions": self.decision_history[player_id][-5:]
        }
    
    def make_decision(self, player_id: int, decision_type: str, game, options: Dict = None) -> Any:
        """Request a decision from the AI for a specific player."""
        # Get comprehensive game context
        context = self.get_game_context(player_id, game)
        
        # Add current decision context
        decision_context = {
            "decision_type": decision_type,
            "options": options or {},
            "game_context": context
        }
        
        # Get AI agent
        agent = self.ai_agents[player_id]
        
        # Make decision with full context
        decision = agent.make_decision(
            game_state=context,
            decision_type=decision_type,
            options=options or {}
        )
        
        # Record decision
        self.decision_history[player_id].append({
            "turn": self.current_turn,
            "type": decision_type,
            "decision": decision,
            "context": options
        })
        
        # Log event
        self.add_event(GameEvent(
            turn=self.current_turn,
            player_id=player_id,
            event_type=f"decision_{decision_type}",
            details={"decision": decision, "options": options}
        ))
        
        return decision
    
    def add_event(self, event: GameEvent):
        """Add a game event to history."""
        self.game_events.append(event)
        
    def add_game_action(self, player_id: int, action: str, details: Dict):
        """Add a game action to history."""
        self.add_event(GameEvent(
            turn=self.current_turn,
            player_id=player_id,
            event_type=action,
            details=details
        ))
    
    def enable_ai_chat(self, player_id: int, game, context: str = "", force: bool = False) -> Optional[str]:
        """Allow AI to send a chat message based on game state."""
        if not self.enable_chat:
            return None
        
        # Check if we recently sent a message (avoid spam) - but allow forced messages
        if not force and "Responding to:" not in context:
            recent_chat = [m for m in self.chat_history[-2:] if m.sender_id == player_id]
            if recent_chat and (datetime.now() - recent_chat[-1].timestamp).seconds < 20:
                return None  # Too soon since last message
        
        # Get game context
        game_context = self.get_game_context(player_id, game)
        
        # Get recent chat for context
        chat_context = self.get_chat_context() if self.chat_history else "No previous messages."
        
        # Create chat prompt based on context
        if "Responding to:" in context:
            # Extract the message we're responding to
            opponent_msg = context.split("Responding to: '")[1].rstrip("'")
            chat_prompt = f"""Your opponent just said: "{opponent_msg}"

Respond directly to their message in under 25 words. Be strategic, friendly, or playful.

Game situation:
- You: ${game_context['my_status']['cash']}, {len(game_context['my_status']['properties'])} properties
- Them: ${game_context['opponents'][0]['cash'] if game_context['opponents'] else 0}, {len(game_context['opponents'][0]['properties']) if game_context['opponents'] else 0} properties

Reply with a SHORT response or 'SKIP'."""
        else:
            # Different prompts based on context
            if "Just decided to" in context:
                chat_prompt = f"""You {context}. Comment on your strategic decision in under 20 words.
Be confident, strategic, or playful about your choice.

Game situation:
- You: ${game_context['my_status']['cash']}, {len(game_context['my_status']['properties'])} properties
- Them: ${game_context['opponents'][0]['cash'] if game_context['opponents'] else 0}, {len(game_context['opponents'][0]['properties']) if game_context['opponents'] else 0} properties

Reply with a SHORT comment or 'SKIP'."""
            elif "Just paid" in context:
                chat_prompt = f"""You {context}. React to this payment in under 20 words.
You can be frustrated, strategic, or humorous.

Your cash: ${game_context['my_status']['cash']}

Reply with a SHORT reaction or 'SKIP'."""
            elif "Just built" in context:
                chat_prompt = f"""You {context}. Boast or comment about your development in under 20 words.

Reply with a SHORT message or 'SKIP'."""
            elif "End of turn" in context:
                chat_prompt = f"""Your turn is ending. {context}

Send a brief message to your opponent (under 20 words). You can:
- Comment on your turn
- Taunt about your position
- Make a strategic remark
- Challenge your opponent

Game state: You have ${game_context['my_status']['cash']} and {len(game_context['my_status']['properties'])} properties

Reply with a SHORT message or 'SKIP'."""
            else:
                chat_prompt = f"""Based on the current game state, you may send ONE short message to your opponent.
Keep it strategic, friendly, and under 30 words. Focus on: {context}

Recent chat:
{chat_context}

Game situation:
- You: ${game_context['my_status']['cash']}, {len(game_context['my_status']['properties'])} properties
- Them: ${game_context['opponents'][0]['cash'] if game_context['opponents'] else 0}, {len(game_context['opponents'][0]['properties']) if game_context['opponents'] else 0} properties

Reply with a SHORT message or 'SKIP'. Do not repeat previous topics."""
        
        agent = self.ai_agents[player_id]
        
        # Get chat decision
        try:
            response = agent.client.chat.completions.create(
                model=agent.model,
                messages=[
                    {"role": "system", "content": "You are a Monopoly player who can chat with opponents. Be concise, strategic, and avoid repeating topics. Each message should be unique and relevant to the current game situation."},
                    {"role": "user", "content": chat_prompt}
                ],
                max_tokens=50,
                temperature=0.9  # More variety in responses
            )
            
            message = response.choices[0].message.content.strip()
            
            if message and message.upper() != "SKIP":
                chat_msg = ChatMessage(
                    sender_id=player_id,
                    sender_name=self.player_names[player_id],
                    message=message,
                    turn=self.current_turn
                )
                self.chat_history.append(chat_msg)
                return message
                
        except Exception as e:
            print(f"Chat error: {e}")
        
        return None
    
    def get_chat_context(self) -> str:
        """Get recent chat history as context."""
        if not self.chat_history:
            return "No chat messages yet."
        
        recent = self.chat_history[-10:]
        return "\n".join([f"{m.sender_name}: {m.message}" for m in recent])
    
    def next_turn(self):
        """Advance to next turn."""
        self.current_turn += 1
    
    def get_game_summary(self) -> Dict:
        """Get a summary of the game so far."""
        return {
            "turn": self.current_turn,
            "total_events": len(self.game_events),
            "chat_messages": len(self.chat_history),
            "events_by_type": self._count_events_by_type(),
            "decisions_by_player": {
                name: len(decisions) 
                for name, decisions in zip(self.player_names, self.decision_history.values())
            }
        }
    
    def _count_events_by_type(self) -> Dict[str, int]:
        """Count events by type."""
        counts = {}
        for event in self.game_events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts
    
    def export_game_history(self, filename: str):
        """Export complete game history to JSON file."""
        history = {
            "players": self.player_names,
            "total_turns": self.current_turn,
            "events": [e.to_dict() for e in self.game_events],
            "chat": [m.to_dict() for m in self.chat_history],
            "decisions": {
                self.player_names[i]: decisions 
                for i, decisions in self.decision_history.items()
            },
            "summary": self.get_game_summary()
        }
        
        with open(filename, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"Game history exported to {filename}")