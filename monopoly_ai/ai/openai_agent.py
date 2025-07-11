"""OpenAI-powered Monopoly AI agent using function calling."""
import os
import json
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Try to import colors
try:
    from utils.colors import *
    USE_COLORS = True
except ImportError:
    USE_COLORS = False
    def decision(decision_type, choice, reasoning=None):
        return f"Decision: {decision_type} -> {choice}" + (f"\nReasoning: {reasoning}" if reasoning else "")


class OpenAIMonopolyAgent:
    """AI agent that uses OpenAI's function calling to make decisions."""
    
    def __init__(self, agent_name: str = "AI Player", model: str = "gpt-4.1-nano"):
        self.agent_name = agent_name
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        
    def make_decision(self, game_state: Dict, decision_type: str, options: Dict) -> Any:
        """Make a decision using OpenAI function calling."""
        
        # Define available functions based on decision type
        functions = self._get_functions_for_decision(decision_type)
        
        # Create the prompt
        prompt = self._create_prompt(game_state, decision_type, options)
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        try:
            # Call OpenAI with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    *self.conversation_history[-10:]  # Keep last 10 messages for context
                ],
                functions=functions,
                function_call="auto"
            )
            
            message = response.choices[0].message
            
            # Check if function was called
            if message.function_call:
                function_name = message.function_call.name
                function_args = json.loads(message.function_call.arguments)
                
                # Log the decision
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"Decision: {function_name} with args {function_args}"
                })
                
                return self._parse_function_result(function_name, function_args)
            else:
                # Fallback to content parsing
                return self._parse_text_response(message.content, decision_type)
                
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fallback to simple heuristics
            return self._fallback_decision(decision_type, options)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI."""
        return f"""You are {self.agent_name}, a Monopoly player. Your objective is to win the game.

MONOPOLY RULES:

1. PROPERTY ACQUISITION:
   - When you land on an unowned property, you can BUY it at the listed price or PASS
   - If you pass, the property goes to AUCTION where all players can bid
   - Properties can also be obtained through TRADES with other players

2. AUCTIONS:
   - All players participate in auctions simultaneously
   - Initial bids are secret and revealed at the same time
   - You can bid any amount from $1 to your available cash
   - The base price is the property's listed price (for reference only)
   - Highest bidder wins the property

3. MORTGAGING:
   - You can mortgage properties to receive 50% of their purchase price
   - Mortgaged properties cannot collect rent
   - To unmortgage: pay the mortgage amount plus 10% interest
   - Properties with houses/hotels cannot be mortgaged

4. TRADING:
   - You can propose trades during your turn
   - Possible trade combinations:
     * Properties for properties
     * Cash for properties
     * Properties + cash for properties + cash
   - The other player can accept, reject, or make a counter-offer

5. BUILDING:
   - You can build houses/hotels only on complete color groups (monopolies)
   - Houses must be built evenly across all properties in the color group
   - Maximum 4 houses per property, then can upgrade to 1 hotel

6. RENT:
   - Collect rent when opponents land on your properties
   - Rent increases with houses/hotels
   - No rent collected on mortgaged properties

7. WINNING:
   - Last player remaining (all others bankrupt) wins
   - Bankruptcy occurs when a player cannot pay debts"""

    def _create_prompt(self, game_state: Dict, decision_type: str, options: Dict) -> str:
        """Create a prompt for the current decision."""
        # Handle both formats - from game_state directly or from nested my_status
        if 'my_status' in game_state:
            my_status = game_state['my_status']
            opponents = game_state.get('opponents', [])
            opponent = opponents[0] if opponents else None
        else:
            # Fallback format
            my_status = game_state.get('current_player', {})
            opponent = game_state.get('opponent', {})
        
        prompt_parts = [
            f"Current game state:",
            f"- My cash: ${my_status.get('cash', 0)}",
            f"- My properties: {len(my_status.get('properties', []))}",
            f"- My position: {my_status.get('position', 0)}",
        ]
        
        if opponent:
            prompt_parts.extend([
                f"- Opponent cash: ${opponent.get('cash', 0)}",
                f"- Opponent properties: {len(opponent.get('properties', []))}"
            ])
        
        prompt_parts.append(f"\nDecision needed: {decision_type}")
        
        if options:
            prompt_parts.append(f"Options: {json.dumps(options, indent=2)}")
        
        return "\n".join(prompt_parts)
    
    def _get_functions_for_decision(self, decision_type: str) -> List[Dict]:
        """Get function definitions based on decision type."""
        
        if decision_type == "buy_property":
            return [{
                "name": "decide_buy_property",
                "description": "Decide whether to buy a property",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "buy": {
                            "type": "boolean",
                            "description": "True to buy, False to pass"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the decision"
                        }
                    },
                    "required": ["buy", "reasoning"]
                }
            }]
        
        elif decision_type == "jail_strategy":
            return [{
                "name": "decide_jail_action",
                "description": "Decide how to get out of jail",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["use_card", "pay_bail", "roll_dice"],
                            "description": "The action to take"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the decision"
                        }
                    },
                    "required": ["action", "reasoning"]
                }
            }]
        
        elif decision_type == "build_houses":
            return [{
                "name": "decide_build",
                "description": "Decide whether and where to build houses/hotels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "build": {
                            "type": "boolean",
                            "description": "True to build, False to skip"
                        },
                        "property_name": {
                            "type": "string",
                            "description": "Name of property to build on (if building)"
                        },
                        "num_houses": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "Number of houses to build (5 = hotel)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the decision"
                        }
                    },
                    "required": ["build", "reasoning"]
                }
            }]
        
        elif decision_type == "mortgage_decision":
            return [{
                "name": "decide_mortgage",
                "description": "Decide which properties to mortgage to raise cash. Mortgaging gives you 50% of property value but you can't collect rent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "properties_to_mortgage": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of property names to mortgage"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the decision"
                        }
                    },
                    "required": ["properties_to_mortgage", "reasoning"]
                }
            }]
        
        elif decision_type == "proactive_mortgage":
            return [{
                "name": "decide_proactive_mortgage",
                "description": "Decide whether to mortgage properties proactively for cash flow",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mortgage": {
                            "type": "boolean",
                            "description": "True to mortgage properties, False to keep them"
                        },
                        "properties_to_mortgage": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of property names to mortgage if mortgaging"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Strategic explanation"
                        }
                    },
                    "required": ["mortgage", "reasoning"]
                }
            }]
        
        elif decision_type == "trade_proposal":
            return [{
                "name": "propose_trade",
                "description": "Propose a trade with another player",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offer_properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Properties I'm offering"
                        },
                        "offer_cash": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Cash I'm offering"
                        },
                        "request_properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Properties I want"
                        },
                        "request_cash": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Cash I want"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the trade"
                        }
                    },
                    "required": ["offer_properties", "offer_cash", "request_properties", "request_cash", "reasoning"]
                }
            }]
        
        elif decision_type == "auction_initial_bid":
            return [{
                "name": "make_initial_bid",
                "description": "Make a secret initial bid in the property auction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bid_amount": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Your bid amount in dollars (any amount from $0 to your available cash). $0 means you don't want to bid."
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for your decision"
                        }
                    },
                    "required": ["bid_amount", "reasoning"]
                }
            }]
        
        elif decision_type == "auction_counter_bid":
            return [{
                "name": "make_counter_bid",
                "description": "Decide whether to raise bid in auction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bid": {
                            "type": "boolean",
                            "description": "True to raise bid, False to drop out"
                        },
                        "new_bid": {
                            "type": "integer",
                            "description": "New bid amount if bidding"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the decision"
                        }
                    },
                    "required": ["bid", "reasoning"]
                }
            }]
        
        elif decision_type == "trade_response":
            return [{
                "name": "respond_to_trade",
                "description": "Respond to a trade offer from another player",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "accept": {
                            "type": "boolean",
                            "description": "True to accept the trade as-is"
                        },
                        "counter_offer": {
                            "type": "object",
                            "description": "If not accepting, provide a counter offer",
                            "properties": {
                                "offer_properties": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Properties you're willing to give"
                                },
                                "offer_cash": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "description": "Cash you're willing to give"
                                },
                                "request_properties": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Properties you want in return"
                                },
                                "request_cash": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "description": "Cash you want in return"
                                }
                            }
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for your response"
                        }
                    },
                    "required": ["accept", "reasoning"]
                }
            }]
        
        elif decision_type == "initiate_trade":
            return [{
                "name": "decide_trade_initiation",
                "description": "Decide whether to initiate a trade with another player",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "initiate": {
                            "type": "boolean",
                            "description": "True to propose a trade"
                        },
                        "target_player": {
                            "type": "string",
                            "description": "Name of player to trade with"
                        },
                        "offer_properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Properties to offer"
                        },
                        "offer_cash": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Cash to offer"
                        },
                        "request_properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Properties to request"
                        },
                        "request_cash": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Cash to request"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Strategic explanation"
                        }
                    },
                    "required": ["initiate", "reasoning"]
                }
            }]
        
        return []
    
    def _parse_function_result(self, function_name: str, args: Dict) -> Any:
        """Parse function call results into decision."""
        reasoning = args.get('reasoning', 'Making decision...')
        if USE_COLORS:
            # Map function names to decision types for display
            decision_types = {
                "decide_buy_property": "Property Purchase",
                "decide_jail_action": "Jail Strategy",
                "decide_build": "Building Decision",
                "decide_mortgage": "Mortgage Strategy",
                "propose_trade": "Trade Proposal"
            }
            decision_type = decision_types.get(function_name, function_name)
            
            # Format the choice
            if function_name == "decide_buy_property":
                choice = "Buy" if args["buy"] else "Pass"
            elif function_name == "decide_jail_action":
                choice = args["action"].replace("_", " ").title()
            elif function_name == "decide_build":
                choice = f"Build on {args.get('property_name', 'property')}" if args["build"] else "Skip building"
            else:
                choice = str(args)
            
            print(decision(decision_type, choice, reasoning))
        else:
            print(f"🤖 {self.agent_name}: {reasoning}")
        
        if function_name == "decide_buy_property":
            return args["buy"]
        elif function_name == "decide_jail_action":
            return args["action"]
        elif function_name == "decide_build":
            return {
                "build": args["build"],
                "property": args.get("property_name"),
                "houses": args.get("num_houses", 1)
            }
        elif function_name == "decide_mortgage":
            return args["properties_to_mortgage"]
        elif function_name == "propose_trade":
            return {
                "offer": {
                    "properties": args["offer_properties"],
                    "cash": args["offer_cash"]
                },
                "request": {
                    "properties": args["request_properties"],
                    "cash": args["request_cash"]
                }
            }
        elif function_name == "make_initial_bid":
            return args["bid_amount"]
        elif function_name == "make_counter_bid":
            return {
                "bid": args["bid"],
                "new_bid": args.get("new_bid", 0)
            }
        elif function_name == "decide_proactive_mortgage":
            return {
                "mortgage": args["mortgage"],
                "properties": args.get("properties_to_mortgage", [])
            }
        elif function_name == "respond_to_trade":
            return {
                "accept": args["accept"],
                "counter_offer": args.get("counter_offer")
            }
        elif function_name == "decide_trade_initiation":
            if args["initiate"]:
                return {
                    "initiate": True,
                    "target_player": args.get("target_player"),
                    "offer_properties": args.get("offer_properties", []),
                    "offer_cash": args.get("offer_cash", 0),
                    "request_properties": args.get("request_properties", []),
                    "request_cash": args.get("request_cash", 0)
                }
            return {"initiate": False}
        
        return None
    
    def _parse_text_response(self, content: str, decision_type: str) -> Any:
        """Parse text response as fallback."""
        content_lower = content.lower()
        
        if decision_type == "buy_property":
            return "buy" in content_lower or "yes" in content_lower
        elif decision_type == "jail_strategy":
            if "card" in content_lower:
                return "use_card"
            elif "pay" in content_lower or "bail" in content_lower:
                return "pay_bail"
            else:
                return "roll_dice"
        
        return None
    
    def _fallback_decision(self, decision_type: str, options: Dict) -> Any:
        """Simple heuristic fallback when API fails."""
        if decision_type == "buy_property":
            # Buy if we have enough cash buffer
            price = options.get("price", 0)
            cash = options.get("cash", 0)
            # More conservative - need more buffer to trigger auctions
            return cash > price + 800
        elif decision_type == "jail_strategy":
            if options.get("has_card"):
                return "use_card"
            elif options.get("cash", 0) > 50:
                return "pay_bail"
            else:
                return "roll_dice"
        elif decision_type == "build_houses":
            return {"build": False}
        
        return None