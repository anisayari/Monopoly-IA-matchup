"""
Définitions des popups Monopoly pour référence
"""

MONOPOLY_POPUPS = {
    "turn_options": {
        "name": "would you like to",
        "text_patterns": ["would you like to"],
        "expected_buttons": ["accounts", "next turn", "roll again"],
        "action": "Choose turn action"
    },
    
    "property_purchase": {
        "name": "you want to buy",
        "text_patterns": ["you want to buy", "do you want to buy"],
        "expected_buttons": ["auction", "buy"],
        "action": "Buy or auction property"
    },
    
    "property_management": {
        "name": "a Property you own",
        "text_patterns": ["a property you own"],
        "expected_buttons": ["back", "trade"],
        "action": "Manage owned properties"
    },
    
    "chance_card": {
        "name": "chance",
        "text_patterns": ["chance"],
        "expected_buttons": ["ok"],
        "action": "Acknowledge chance card"
    },
    
    "jail_decision": {
        "name": "In Jail",
        "text_patterns": ["in jail"],
        "expected_buttons": ["pay bail", "roll dice", "use card"],
        "action": "Choose jail action"
    },
    
    "community_chest": {
        "name": "Community Chest",
        "text_patterns": ["community chest"],
        "expected_buttons": ["ok"],
        "action": "Acknowledge community chest"
    },
    
    "auction_bid": {
        "name": "Auction",
        "text_patterns": ["bid"],
        "expected_buttons": ["yes", "no"],
        "action": "Decide to bid in auction"
    },
    
    "accounts_info": {
        "name": "Accounts 1",
        "text_patterns": ["accounts"],
        "expected_buttons": ["ok"],
        "action": "View account information"
    },
    
    "accounts_management": {
        "name": "Accounts 2",
        "text_patterns": ["accounts"],
        "expected_buttons": ["back", "trade"],
        "action": "Manage accounts"
    },
    
    "trading_select_player": {
        "name": "Trading 1",
        "text_patterns": ["select player"],
        "expected_buttons": [],  # Dynamic player names
        "action": "Select player to trade with"
    },
    
    "trading_select_properties": {
        "name": "Trading 2",
        "text_patterns": ["choose wich properties you want to trade", "choose which properties"],
        "expected_buttons": [],  # Dynamic property selection
        "action": "Select properties for trade"
    },
    
    "trading_negotiate": {
        "name": "Trading 3",
        "text_patterns": ["trading"],
        "expected_buttons": ["cancel", "propose", "request cash", "add cash"],
        "action": "Negotiate trade terms"
    },
    
    "trading_confirm": {
        "name": "Trading 4",
        "text_patterns": ["trading"],
        "expected_buttons": ["deal", "no deal"],
        "action": "Confirm or reject trade"
    },
    
    "pay_rent": {
        "name": "Pay Rent",
        "text_patterns": ["pay rent"],
        "expected_buttons": ["ok"],
        "action": "Pay rent to property owner"
    },
    
    "go_to_jail": {
        "name": "Go to Jail",
        "text_patterns": ["go to jail"],
        "expected_buttons": ["ok"],
        "action": "Go directly to jail"
    },
    
    "property_deeds": {
        "name": "Property Deeds",
        "text_patterns": ["property deeds"],
        "expected_buttons": ["mortage", "buy 1", "buy set", "sell 1", "sell set", "done"],
        "action": "Manage property improvements"
    }
}

def get_popup_info(popup_type: str) -> dict:
    """Récupère les informations d'un type de popup"""
    return MONOPOLY_POPUPS.get(popup_type, {
        "name": "unknown",
        "text_patterns": [],
        "expected_buttons": [],
        "action": "Unknown action"
    })

def get_expected_action(popup_type: str) -> str:
    """Récupère l'action attendue pour un type de popup"""
    popup_info = get_popup_info(popup_type)
    return popup_info.get("action", "Unknown action")