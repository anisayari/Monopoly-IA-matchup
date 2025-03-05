class MemoryAddresses:
    """Centralise toutes les adresses mémoire du jeu"""
    ADDRESSES = {
        "BLUE_LABEL": [0x804DFDA1, 0x8051C0E5, 0x9303DB75, 0x90023179],
        "RED_LABEL": [0x804DFDCB, 0x8051C1E5, 0x9303DD65, 0x90025439],
        "RED_MONEY": [0x9003C0C6, 0x9303DD5E],
        "RED_MONEY_LABEL": [0x90024B5B],
        "BLUE_MONEY": [0x9003C0BA, 0x9303DB6E],
        "BLUE_MONEY_LABEL": [0x900226D3],
        "BLUE_GOTO": [0x804ED3AB, 0x804F63AB, 0x804F63AF],
        "BLUE_POSITION": [0x804ED3AF, 0x804F63AF],
        "RED_GOTO": [0x804ED8EB, 0x804F63AB],
        "RED_POSITION": [0x804ED8EF, 0x804F63AF],
        "BLUE_DICE_1": [0x9303DA6B],
        "BLUE_DICE_2": [0x9303DA6F],
        "RED_DICE_1": [0x9303DC5B],
        "RED_DICE_2": [0x9303DC5F],
        "BLUE_DICE_SUM": [0x9303DA7B],
        "RED_DICE_SUM": [0x9303DC6B],
        "DIALOG_ROLL_DICE_TITLE": [0x8052E5E1],
        "DIALOG_ROLL_DICE_MESSAGE": [0x8052E661],
        "DIALOG_AUCTION_BID_MESSAGE": [0x90053429],
        "DIALOG_AUCTION_PURCHASER_NAME": [0x90053049],
        "DIALOG_AUCTION_MESSAGE_NAME": [0x90050F09]
        }
    
    PROPERTY_RANGE = (0x92B96E5C, 0x92B97529) 