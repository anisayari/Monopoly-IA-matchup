"""Terminal color utilities for better game visualization."""

class Colors:
    """ANSI color codes for terminal output."""
    # Reset
    RESET = '\033[0m'
    
    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'


class GameColors:
    """Semantic color mappings for game elements."""
    # Player colors
    PLAYER1 = Colors.BRIGHT_CYAN
    PLAYER2 = Colors.BRIGHT_MAGENTA
    
    # Game elements
    MONEY = Colors.BRIGHT_GREEN
    PROPERTY = Colors.BRIGHT_YELLOW
    ACTION = Colors.BRIGHT_BLUE
    WARNING = Colors.BRIGHT_RED
    SUCCESS = Colors.BRIGHT_GREEN
    
    # Chat
    CHAT = Colors.BRIGHT_WHITE
    
    # Board elements
    HEADER = Colors.BOLD + Colors.BRIGHT_WHITE
    DIVIDER = Colors.BRIGHT_BLACK
    
    # Property colors (matching Monopoly board)
    BROWN = Colors.YELLOW  # Using yellow as brown doesn't exist
    LIGHT_BLUE = Colors.BRIGHT_CYAN
    PINK = Colors.BRIGHT_MAGENTA
    ORANGE = Colors.BRIGHT_YELLOW
    RED = Colors.BRIGHT_RED
    YELLOW = Colors.BRIGHT_YELLOW
    GREEN = Colors.BRIGHT_GREEN
    DARK_BLUE = Colors.BRIGHT_BLUE
    
    # Special squares
    SPECIAL = Colors.BRIGHT_WHITE
    TAX = Colors.RED
    RAILROAD = Colors.WHITE
    UTILITY = Colors.CYAN


def colored(text: str, color: str) -> str:
    """Wrap text with color codes."""
    return f"{color}{text}{Colors.RESET}"


def money(amount: int) -> str:
    """Format money with color."""
    return colored(f"${amount}", GameColors.MONEY)


def property_name(name: str, color_type: str = None) -> str:
    """Format property name with appropriate color."""
    if color_type:
        color_map = {
            "brown": GameColors.BROWN,
            "light_blue": GameColors.LIGHT_BLUE,
            "pink": GameColors.PINK,
            "orange": GameColors.ORANGE,
            "red": GameColors.RED,
            "yellow": GameColors.YELLOW,
            "green": GameColors.GREEN,
            "dark_blue": GameColors.DARK_BLUE,
        }
        color = color_map.get(color_type, GameColors.PROPERTY)
    else:
        color = GameColors.PROPERTY
    return colored(name, color)


def player_name(name: str, player_id: int) -> str:
    """Format player name with their color."""
    color = GameColors.PLAYER1 if player_id == 0 else GameColors.PLAYER2
    return colored(name, color)


def action(text: str) -> str:
    """Format action text."""
    return colored(text, GameColors.ACTION)


def warning(text: str) -> str:
    """Format warning text."""
    return colored(text, GameColors.WARNING)


def success(text: str) -> str:
    """Format success text."""
    return colored(text, GameColors.SUCCESS)


def chat_message(sender: str, message: str, sender_id: int, is_response: bool = False) -> str:
    """Format chat message with colors."""
    sender_colored = player_name(sender, sender_id)
    icon = '↩️ ' if is_response else '💬'
    return f"{colored(icon, GameColors.CHAT)} {sender_colored}: {colored(message, GameColors.CHAT)}"


def header(text: str) -> str:
    """Format header text."""
    return colored(text, GameColors.HEADER)


def divider(char: str = "=", length: int = 80) -> str:
    """Create a colored divider."""
    return colored(char * length, GameColors.DIVIDER)


def dice(die1: int, die2: int) -> str:
    """Format dice roll with emoji and colors."""
    dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    total = die1 + die2
    dice_str = f"{dice_faces[die1]} {dice_faces[die2]}"
    
    if die1 == die2:
        return f"{colored(dice_str, Colors.BRIGHT_YELLOW)} = {colored(str(total), Colors.BRIGHT_YELLOW)} {colored('DOUBLES!', Colors.BOLD + Colors.BRIGHT_YELLOW)}"
    else:
        return f"{dice_str} = {total}"


def board_position(position: int, square_name: str, square_type: str) -> str:
    """Format board position with appropriate color."""
    type_colors = {
        "property": GameColors.PROPERTY,
        "railroad": GameColors.RAILROAD,
        "utility": GameColors.UTILITY,
        "tax": GameColors.TAX,
        "special": GameColors.SPECIAL,
        "go": GameColors.SUCCESS,
        "jail": GameColors.WARNING,
        "free_parking": GameColors.SPECIAL,
        "go_to_jail": GameColors.WARNING,
        "chance": GameColors.ACTION,
        "community_chest": GameColors.ACTION,
    }
    
    color = type_colors.get(square_type, Colors.WHITE)
    return f"[{position:2d}] {colored(square_name, color)}"


def decision(decision_type: str, choice: str, reasoning: str = None) -> str:
    """Format AI decision with colors."""
    decision_str = f"{colored('🤖 Decision:', Colors.BOLD)} {colored(decision_type, GameColors.ACTION)} → {colored(choice, GameColors.SUCCESS)}"
    if reasoning:
        decision_str += f"\n   {colored('Reasoning:', Colors.DIM)} {reasoning}"
    return decision_str


# Test the colors
if __name__ == "__main__":
    print(header("=== Color Test ==="))
    print(f"Money: {money(1500)}")
    print(f"Player 1: {player_name('AI Alpha', 0)}")
    print(f"Player 2: {player_name('AI Beta', 1)}")
    print(f"Property: {property_name('Park Place', 'dark_blue')}")
    print(f"Action: {action('Rolling dice...')}")
    print(f"Warning: {warning('Low on cash!')}")
    print(f"Success: {success('Property purchased!')}")
    print(f"Chat: {chat_message('AI Alpha', 'Nice move!', 0)}")
    print(f"Dice: {dice(3, 3)}")
    print(f"Dice: {dice(2, 5)}")
    print(divider())