"""Battle mode for two OpenAI-powered AI players."""
import os
import sys
import time
import random
from datetime import datetime
from game import MonopolyGame
from game.trade import TradeOffer
from ai.game_manager import MonopolyGameManager
from ai import AIContext, get_state
from dotenv import load_dotenv
from utils.colors import *
import random

# Load environment variables
load_dotenv()

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: Please set OPENAI_API_KEY in .env file")
    print("Copy .env.example to .env and add your OpenAI API key")
    sys.exit(1)


def display_chat_message(sender: str, message: str, sender_id: int, is_response: bool = False):
    """Display a chat message with formatting."""
    print(f"\n{chat_message(sender, message, sender_id, is_response)}")


def display_turn_header(turn: int, name: str, cash: int, player_id: int):
    """Display turn header."""
    print(f"\n{divider()}")
    print(header(f"TURN {turn} - {player_name(name, player_id)}'s turn ({money(cash)})"))
    print(divider())


def run_ai_turn_with_manager(game: MonopolyGame, player_id: int, manager: MonopolyGameManager):
    """Run an AI turn using the game manager for decisions."""
    player = game.players[player_id]
    
    # Track turn events
    turn_summary = {
        "bought": [],
        "paid_rent": 0,
        "landed_on": [],
        "special_events": []
    }
    
    # Log turn start
    manager.add_game_action(player_id, "turn_start", {"cash": player.cash})
    
    # ALWAYS respond to opponent's last message at turn start
    if manager.chat_history and manager.current_turn > 1:
        last_message = manager.chat_history[-1]
        # If the last message was from the opponent
        if last_message.sender_id != player_id:
            response_context = f"Responding to: '{last_message.message}'"
            chat_response = manager.enable_ai_chat(player_id, game, response_context, force=True)
            if chat_response:
                display_chat_message(player.name, chat_response, player_id, is_response=True)
                time.sleep(1.2)  # Brief pause for readability
    
    # Handle jail
    if game.is_in_jail(player_id):
        print(f"🔒 {warning(f'{player_name(player.name, player_id)} is in jail!')}")
        
        options = {
            "has_card": game.has_get_out_card(player_id),
            "cash": player.cash,
            "jail_turns": player.jail_turns
        }
        
        decision = manager.make_decision(player_id, "jail_strategy", game, options)
        
        # Comment on jail decision (70% chance)
        if random.random() < 0.7:
            jail_context = f"Decided to {decision.replace('_', ' ')} to get out of jail"
            comment = manager.enable_ai_chat(player_id, game, jail_context)
            if comment:
                display_chat_message(player.name, comment, player_id)
                time.sleep(0.8)
        
        if decision == "use_card":
            game.use_get_out_card(player_id)
            manager.add_game_action(player_id, "use_jail_card", {})
        elif decision == "pay_bail":
            game.pay_bail(player_id)
            manager.add_game_action(player_id, "pay_bail", {"amount": 50})
        else:
            if not game.roll_for_doubles(player_id):
                manager.add_game_action(player_id, "jail_roll_failed", {})
                return
            manager.add_game_action(player_id, "jail_roll_success", {})
    
    # Roll dice and move
    if not game.is_in_jail(player_id):
        roll = game.roll_dice(player_id)
        manager.add_game_action(player_id, "dice_roll", {
            "die1": roll.die1, 
            "die2": roll.die2, 
            "total": roll.total
        })
        
        game.move_player_token(player_id)
        square = game.current_square(player_id)
        manager.add_game_action(player_id, "land_on", {
            "position": player.position,
            "square": square.name
        })
        
        # Handle landing
        if square.is_property() and square.owner is None:
            # Unowned property - decide to buy
            options = {
                "property_name": square.name,
                "price": square.price,
                "cash": player.cash,
                "color": square.color.value if hasattr(square, 'color') and square.color else None
            }
            
            should_buy = manager.make_decision(player_id, "buy_property", game, options)
            
            # Comment on decision (60% chance)
            if random.random() < 0.6:
                decision_context = f"Just decided to {'buy' if should_buy else 'pass on'} {square.name}"
                comment = manager.enable_ai_chat(player_id, game, decision_context)
                if comment:
                    display_chat_message(player.name, comment, player_id)
                    time.sleep(0.8)
            
            if should_buy:
                if game.buy_property(player_id):
                    manager.add_game_action(player_id, "buy_property", {
                        "property": square.name,
                        "price": square.price
                    })
                    turn_summary["bought"].append(square.name)
            else:
                # Start auction with manager
                print(f"\n{warning(f'{player_name(player.name, player_id)} passes on {property_name(square.name)}')}")
                time.sleep(1)
                
                if game.start_auction(manager):
                    turn_summary["special_events"].append(f"auction for {square.name}")
                
                manager.add_game_action(player_id, "pass_property", {"property": square.name})
                
        elif square.is_property() and square.owner != player_id:
            # Pay rent
            owner = game.players[square.owner]
            rent = square.get_rent(roll.total if roll else None)
            
            manager.add_game_action(player_id, "pay_rent", {
                "to": owner.name,
                "amount": rent,
                "property": square.name
            })
            
            game.pay_rent(player_id)
            turn_summary["paid_rent"] += rent
            
            # Always comment on high rent
            if rent > 50:
                rent_context = f"Just paid ${rent} rent on {square.name} to {owner.name}"
                comment = manager.enable_ai_chat(player_id, game, rent_context)
                if comment:
                    display_chat_message(player.name, comment, player_id)
                    time.sleep(0.8)
            
            # Check if player needs to mortgage
            if player.cash < 0:
                # Get mortgage decision
                options = {
                    "cash_needed": -player.cash,
                    "properties": [
                        {"name": game.board[p].name, "value": game.board[p].mortgage_value}
                        for p in player.properties
                        if hasattr(game.board[p], 'mortgaged') and not game.board[p].mortgaged
                    ]
                }
                
                mortgage_decision = manager.make_decision(player_id, "mortgage_decision", game, options)
                game.mortgage_until_positive(player_id)
                game.settle_negative_cash(player_id)
                
        elif square.is_tax():
            game.pay_tax(player_id)
            manager.add_game_action(player_id, "pay_tax", {"square": square.name})
            
        elif square.is_special():
            game.execute_special_square(player_id)
            manager.add_game_action(player_id, "special_square", {"square": square.name})
            
            # Comment on special squares (50% chance)
            if square.square_type.value in ["chance", "community_chest", "go_to_jail"] and random.random() < 0.5:
                special_context = f"Landed on {square.name}"
                comment = manager.enable_ai_chat(player_id, game, special_context)
                if comment:
                    display_chat_message(player.name, comment, player_id)
                    time.sleep(0.8)
        
        # Check for doubles
        if roll.is_doubles:
            game.doubles_count += 1
            if game.doubles_count >= 3:
                game.send_player_to_jail(player_id)
                manager.add_game_action(player_id, "jail_from_doubles", {})
            else:
                print(f"🎲 {success(f'Doubles! {player_name(player.name, player_id)} rolls again.')}")
                # Allow chat before rolling again
                chat = manager.enable_ai_chat(player_id, game, "Rolled doubles!")
                if chat:
                    display_chat_message(player.name, chat, player_id)
                time.sleep(1)
                run_ai_turn_with_manager(game, player_id, manager)
                return
    
    # Post-turn management
    if game.has_full_monopoly(player_id):
        # Building decision
        from game.board import PropertyColor
        monopolies = []
        for color in PropertyColor:
            if game.has_monopoly(player_id, color):
                monopolies.append(color.value)
        
        options = {
            "cash": player.cash,
            "monopolies": monopolies
        }
        
        build_decision = manager.make_decision(player_id, "build_houses", game, options)
        if build_decision and build_decision.get("build"):
            game.build_houses_or_hotels(player_id)
            manager.add_game_action(player_id, "build", build_decision)
            
            # Comment on building (80% chance)
            if random.random() < 0.8:
                build_context = f"Just built houses on my {monopolies[0] if monopolies else 'monopoly'}"
                comment = manager.enable_ai_chat(player_id, game, build_context)
                if comment:
                    display_chat_message(player.name, comment, player_id)
                    time.sleep(0.8)
    
    # Check if player needs cash and might mortgage
    if player.cash < 200 and len(player.properties) > 0:
        mortgageable = game.get_mortgageable_properties(player_id)
        if mortgageable:
            options = {
                "cash": player.cash,
                "properties": mortgageable
            }
            
            mortgage_decision = manager.make_decision(player_id, "proactive_mortgage", game, options)
            if mortgage_decision and mortgage_decision.get("mortgage"):
                for prop_name in mortgage_decision.get("properties", []):
                    # Find property by name
                    for prop in mortgageable:
                        if prop["name"] == prop_name:
                            game.mortgage_property(player_id, prop["position"])
                            manager.add_game_action(player_id, "mortgage", {
                                "property": prop_name,
                                "value": prop["mortgage_value"]
                            })
                            break
    
    # Check if AI wants to initiate a trade (only check, not force)
    if len(player.properties) > 0 and not player.bankrupt:
        # Find potential trade partners
        other_players = [p for p in game.players if p.id != player_id and not p.bankrupt and len(p.properties) > 0]
        
        if other_players:
            # Provide context about trading opportunities
            options = {
                "my_properties": [game.board[pos].name for pos in player.properties],
                "my_cash": player.cash,
                "opponents": [
                    {
                        "name": p.name,
                        "properties": [game.board[pos].name for pos in p.properties],
                        "cash": p.cash
                    }
                    for p in other_players
                ],
                "game_context": "You can propose trades at any time to complete monopolies or improve your position"
            }
            
            trade_decision = manager.make_decision(player_id, "initiate_trade", game, options)
            
            if trade_decision and trade_decision.get("initiate"):
                # Find target player by name
                target_player = None
                for p in other_players:
                    if p.name == trade_decision.get("target_player"):
                        target_player = p
                        break
                
                if target_player:
                    # Convert property names to positions
                    offer_positions = []
                    request_positions = []
                    
                    for prop_name in trade_decision.get("offer_properties", []):
                        for pos in player.properties:
                            if game.board[pos].name == prop_name:
                                offer_positions.append(pos)
                                break
                    
                    for prop_name in trade_decision.get("request_properties", []):
                        for pos in target_player.properties:
                            if game.board[pos].name == prop_name:
                                request_positions.append(pos)
                                break
                    
                    # Create trade offer
                    offer = TradeOffer(
                        proposer_id=player_id,
                        recipient_id=target_player.id,
                        offer_properties=offer_positions,
                        offer_cash=trade_decision.get("offer_cash", 0),
                        request_properties=request_positions,
                        request_cash=trade_decision.get("request_cash", 0)
                    )
                    
                    # Announce trade attempt
                    print(f"\n💼 {player_name(player.name, player_id)} initiates trade discussion with {player_name(target_player.name, target_player.id)}")
                    time.sleep(1)
                    
                    # Process trade
                    if game.trading_system.propose_trade(offer, manager):
                        manager.add_game_action(player_id, "trade_completed", {
                            "with": target_player.name,
                            "gave": trade_decision.get("offer_properties", []),
                            "received": trade_decision.get("request_properties", [])
                        })
                        turn_summary["special_events"].append(f"trade with {target_player.name}")
    
    # ALWAYS send a message at end of turn
    if not player.bankrupt:
        # Create context based on what happened this turn
        turn_events = []
        if turn_summary["bought"]:
            turn_events.append(f"bought {', '.join(turn_summary['bought'])}")
        if turn_summary["paid_rent"] > 0:
            turn_events.append(f"paid ${turn_summary['paid_rent']} rent")
        if turn_summary.get("built_houses"):
            turn_events.append("built houses")
        
        end_context = f"End of turn summary: {', '.join(turn_events) if turn_events else 'quiet turn, just moved'}"
        chat = manager.enable_ai_chat(player_id, game, end_context, force=True)
        if chat:
            display_chat_message(player.name, chat, player_id)
            time.sleep(0.8)
    
    game.end_turn(player_id)


def run_openai_battle(num_turns: int = 50, delay_between_turns: float = 2.0):
    """Run a battle between two OpenAI-powered AI players."""
    print(header("=== MONOPOLY AI BATTLE ==="))
    print(colored("Two OpenAI-powered AIs compete!", Colors.BRIGHT_CYAN))
    print(f"Using model: {colored('gpt-4.1-nano', Colors.BRIGHT_YELLOW)}")
    print(divider())
    
    # Initialize game and manager
    player_names = ["AI Alpha", "AI Beta"]
    game = MonopolyGame(player_names)
    manager = MonopolyGameManager(player_names, enable_chat=True)
    
    # Make both players AI
    for player in game.players:
        player.is_ai = True
    
    print(f"\n🎮 {success('Game initialized. Let the battle begin!')}\n")
    
    # Initial greeting between AIs
    greeting = manager.enable_ai_chat(0, game, "Game starting - greet your opponent")
    if greeting:
        display_chat_message(player_names[0], greeting, 0)
        time.sleep(1)
        
        # Response from second player
        response_context = f"Responding to: '{greeting}'"
        response = manager.enable_ai_chat(1, game, response_context)
        if response:
            display_chat_message(player_names[1], response, 1, is_response=True)
            time.sleep(1)
    
    time.sleep(1)
    
    # Game loop
    turn = 0
    while not game.game_over and turn < num_turns:
        turn += 1
        manager.next_turn()
        
        current_player = game.current_player
        if current_player.bankrupt:
            continue
        
        display_turn_header(turn, current_player.name, current_player.cash, current_player.id)
        
        # Show current board state
        print(f"\n📊 {header('Current Holdings:')}")
        for p in game.players:
            if not p.bankrupt:
                props = len(p.properties)
                prop_names = [game.board[pos].name for pos in p.properties[:3]]
                if len(p.properties) > 3:
                    prop_names.append(f"...+{len(p.properties)-3} more")
                print(f"  {player_name(p.name, p.id)}: {money(p.cash)} | {colored(f'{props} properties', Colors.BRIGHT_YELLOW)}")
                if prop_names:
                    print(f"    Properties: {colored(', '.join(prop_names), Colors.DIM)}")
        
        # Run turn
        run_ai_turn_with_manager(game, current_player.id, manager)
        
        # Delay for readability
        time.sleep(delay_between_turns)
    
    # Game over
    print(f"\n{divider()}")
    print(header("GAME OVER!"))
    print(divider())
    
    if game.game_over:
        winner = next((p for p in game.players if not p.bankrupt), None)
        if winner:
            print(f"\n🏆 {success(f'{player_name(winner.name, winner.id)} WINS THE GAME!')}")
    else:
        print(f"\n{warning(f'Game ended after {num_turns} turns')}")
        # Determine winner by net worth
        winner = max(game.players, key=lambda p: p.cash if not p.bankrupt else -1)
        print(f"\n🏆 {success(f'{player_name(winner.name, winner.id)} wins with {money(winner.cash)}!')}")
    
    # Final statistics
    print(f"\n{header('Final Statistics:')}")
    for p in game.players:
        print(f"\n{player_name(p.name, p.id)}:")
        status_color = Colors.BRIGHT_RED if p.bankrupt else Colors.BRIGHT_GREEN
        print(f"  Status: {colored('Bankrupt' if p.bankrupt else 'Active', status_color)}")
        print(f"  Cash: {money(p.cash)}")
        print(f"  Properties: {colored(str(len(p.properties)), Colors.BRIGHT_YELLOW)}")
    
    # Show game summary
    summary = manager.get_game_summary()
    print(f"\nGame Summary:")
    print(f"  Total turns: {summary['turn']}")
    print(f"  Total events: {summary['total_events']}")
    print(f"  Chat messages: {summary['chat_messages']}")
    
    # Export game history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"game_history_{timestamp}.json"
    manager.export_game_history(filename)
    
    print(f"\n📝 Full game history exported to: {filename}")


if __name__ == "__main__":
    # Configuration
    num_turns = 100
    delay = 1.5  # seconds between turns
    
    if len(sys.argv) > 1:
        try:
            num_turns = int(sys.argv[1])
        except ValueError:
            print("Usage: python openai_battle.py [num_turns]")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            delay = float(sys.argv[2])
        except ValueError:
            delay = 1.5
    
    # Run the battle
    try:
        run_openai_battle(num_turns, delay)
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()