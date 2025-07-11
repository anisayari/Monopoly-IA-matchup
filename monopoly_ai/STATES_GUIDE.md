# Monopoly AI States and Decisions Guide

This document provides a comprehensive overview of all states in the Monopoly AI state machine and the decisions that need to be made at each state.

## State Machine Overview

The AI uses a hierarchical state machine where each state represents a specific decision point or action in the game. States are organized into logical groups based on their function in the game flow.

## State Categories

### 1. Turn Management States
These states control the overall flow of a player's turn.

#### **AI_Turn** (Root State)
- **Purpose**: Entry point for each AI turn
- **Decisions**: None (automatic transition)
- **Next State**: `SenseState`
- **Description**: This is the root state that initializes the turn flow.

#### **TurnEnd**
- **Purpose**: Finalize the current turn
- **Decisions**: None
- **Actions**: Update game statistics, switch to next player
- **Next State**: None (end of turn)

#### **DoubleCheck**
- **Purpose**: Check if player rolled doubles
- **Decisions**: 
  - Continue turn if doubles (and not 3rd double)
  - End turn if no doubles
  - Go to jail if 3rd double
- **Next States**: 
  - `DiceRoll` (if doubles and < 3)
  - `DC_Prison` (if 3rd double)
  - `TurnEnd` (if no doubles)

#### **DC_Prison**
- **Purpose**: Send player to jail for rolling 3 doubles
- **Actions**: Move player to jail position
- **Next State**: None (end turn)

### 2. Observation States
These states gather information about the current game state.

#### **SenseState**
- **Purpose**: Gather game information
- **Actions**: 
  - Update player's view of board
  - Check opponent positions
  - Calculate net worth
- **Decisions**: None (information gathering only)
- **Next State**: `JailCheck`

#### **JailCheck**
- **Purpose**: Determine if player is in jail
- **Decisions**: Branch based on jail status
- **Next States**:
  - `JailDecision` (if in jail)
  - `DiceRoll` (if not in jail)

### 3. Jail States
These states handle all jail-related decisions and actions.

#### **JailDecision**
- **Purpose**: Initiate jail escape sequence
- **Decisions**: None (routing state)
- **Next State**: `EvaluateReleaseOptions`

#### **EvaluateReleaseOptions** 🤖
- **Purpose**: Decide how to get out of jail
- **AI Decisions**:
  - Use "Get Out of Jail Free" card if available
  - Pay $50 bail if have sufficient cash
  - Roll dice to try for doubles
- **Decision Factors**:
  - Available cash
  - Number of turns in jail
  - Possession of jail card
  - Game stage (early/mid/late)
- **Next States**:
  - `JD_UseCard` (if using card)
  - `JD_PayBail` (if paying bail)
  - `JD_Roll` (if rolling dice)

#### **JD_UseCard**
- **Purpose**: Use "Get Out of Jail Free" card
- **Actions**: Remove card from inventory, release from jail
- **Next State**: `JD_Released`

#### **JD_PayBail**
- **Purpose**: Pay $50 to leave jail
- **Actions**: Deduct $50, release from jail
- **Next State**: `JD_Released`

#### **JD_Roll**
- **Purpose**: Attempt to roll doubles to leave jail
- **Actions**: Roll dice, check for doubles
- **Next States**:
  - `JD_Released` (if doubles)
  - `JD_EndTurn` (if no doubles)

#### **JD_Released**
- **Purpose**: Player successfully left jail
- **Actions**: Update jail status
- **Next State**: `DiceRoll`

#### **JD_EndTurn**
- **Purpose**: End turn while still in jail
- **Next State**: None (turn ends)

### 4. Movement States
These states handle dice rolling and token movement.

#### **DiceRoll**
- **Purpose**: Roll dice for movement
- **Actions**: Generate two random numbers 1-6
- **Next State**: `MoveToken`

#### **MoveToken**
- **Purpose**: Move player's token on board
- **Actions**: 
  - Calculate new position
  - Check if passed GO (+$200)
  - Update position
- **Next State**: `LandingDecision`

### 5. Landing States
These states handle what happens when landing on different square types.

#### **LandingDecision** (Router)
- **Purpose**: Determine type of square landed on
- **Decisions**: Route to appropriate handler
- **Next States**:
  - `LD_PropertyCheck` (if property/railroad/utility)
  - `LD_TaxBranch` (if tax square)
  - `LD_Special` (if special square)
  - `LD_Owned` (default/safety)

#### **LD_PropertyCheck**
- **Purpose**: Check property ownership status
- **Decisions**: Route based on ownership
- **Next States**:
  - `LD_BuyBranch` (if unowned)
  - `LD_Owned` (if owned by self)
  - `LD_RentBranch` (if owned by opponent)

### 5.1 Buy Branch

#### **LD_BuyBranch**
- **Purpose**: Initiate property purchase decision
- **Next State**: `LD_EvalLiquidity`

#### **LD_EvalLiquidity** 🤖
- **Purpose**: Decide whether to buy property
- **AI Decisions**:
  - Buy if cash > price + buffer ($500)
  - Consider property color group
  - Evaluate strategic value
- **Decision Factors**:
  - Current cash
  - Property price
  - Color group completion potential
  - Opponent's properties
  - Game stage
- **Next States**:
  - `LD_Purchase` (if buying)
  - `LD_Auction` (if not buying)

#### **LD_Purchase**
- **Purpose**: Execute property purchase
- **Actions**: 
  - Deduct price from cash
  - Transfer ownership
  - Update property list
- **Next State**: `LD_Done`

#### **LD_Auction**
- **Purpose**: Property goes to auction
- **Actions**: Initiate auction process
- **Next State**: `LD_Done`

### 5.2 Rent Branch

#### **LD_RentBranch**
- **Purpose**: Initiate rent payment
- **Next State**: `LD_PayRent`

#### **LD_PayRent**
- **Purpose**: Calculate and pay rent
- **Actions**:
  - Calculate rent amount
  - Transfer money to owner
- **Next State**: `LD_CheckCash`

#### **LD_CheckCash**
- **Purpose**: Check if player has negative cash
- **Decisions**: Need to raise money?
- **Next States**:
  - `LD_Mortgage` (if cash < 0)
  - `LD_Done` (if cash >= 0)

#### **LD_Mortgage** 🤖
- **Purpose**: Decide which properties to mortgage
- **AI Decisions**:
  - Which properties to mortgage
  - Order of mortgaging
- **Decision Factors**:
  - Cash needed
  - Property values
  - Color group preservation
  - Future rent potential
- **Next State**: `LD_PayAfterMort`

#### **LD_PayAfterMort**
- **Purpose**: Settle debts after mortgaging
- **Actions**: Pay remaining debts or declare bankruptcy
- **Next State**: `LD_Done`

### 5.3 Other Landing States

#### **LD_Special**
- **Purpose**: Handle special squares
- **Actions**:
  - GO: Collect $200
  - Free Parking: Nothing
  - Go to Jail: Send to jail
  - Chance/Community Chest: Draw card
- **Next State**: `LD_Done`

#### **LD_TaxBranch**
- **Purpose**: Handle tax squares
- **Actions**: Pay required tax amount
- **Next State**: `LD_Done`

#### **LD_Owned**
- **Purpose**: Landed on own property
- **Actions**: None (safe landing)
- **Next State**: `LD_Done`

#### **LD_Done** & **LD_Exit**
- **Purpose**: Complete landing sequence
- **Next State**: `PostTurnManagement`

### 6. Post-Turn Management States
These states handle building and trading after movement is complete.

#### **PostTurnManagement**
- **Purpose**: Initiate post-turn activities
- **Next State**: `PTM_ImprovementCheck`

#### **PTM_ImprovementCheck**
- **Purpose**: Check for improvement opportunities
- **Decisions**:
  - Check for complete color groups
  - Check for trade opportunities
- **Next States**:
  - `PTM_BuildBranch` (if have monopoly)
  - `PTM_TradeBranch` (if trade opportunity)
  - `PTM_End` (if neither)

### 6.1 Building Branch

#### **PTM_BuildBranch**
- **Purpose**: Initiate building evaluation
- **Next State**: `PTM_EvalROI`

#### **PTM_EvalROI** 🤖
- **Purpose**: Evaluate building investment
- **AI Decisions**:
  - Whether to build
  - Which properties to build on
  - How many houses/hotels
- **Decision Factors**:
  - Available cash
  - Building costs
  - Expected rent increase
  - Opponent landing probability
  - Cash reserves needed
- **Next States**:
  - `PTM_Build` (if building)
  - `PTM_Skip` (if not building)

#### **PTM_Build**
- **Purpose**: Execute building construction
- **Actions**:
  - Purchase houses/hotels
  - Update property improvements
- **Next State**: `PTM_BuildEnd`

#### **PTM_Skip**
- **Purpose**: Skip building this turn
- **Next State**: `PTM_BuildEnd`

#### **PTM_BuildEnd**
- **Purpose**: Complete building phase
- **Next State**: `PTM_ImprovementCheck` (loop back)

### 6.2 Trading Branch

#### **PTM_TradeBranch**
- **Purpose**: Initiate trading evaluation
- **Next State**: `PTM_FindPartner`

#### **PTM_FindPartner** 🤖
- **Purpose**: Identify best trade partner
- **AI Decisions**:
  - Which player to trade with
  - What properties to target
- **Decision Factors**:
  - Color group completion
  - Breaking opponent monopolies
  - Cash positions
- **Next States**:
  - `PTM_MakeOffer` (if partner found)
  - `PTM_NoTrade` (if no good trades)

#### **PTM_MakeOffer** 🤖
- **Purpose**: Create trade proposal
- **AI Decisions**:
  - Properties to offer
  - Properties to request
  - Cash to include
- **Next State**: `PTM_Wait`

#### **PTM_Wait**
- **Purpose**: Wait for trade response
- **Next States**:
  - `PTM_Accepted` (if accepted)
  - `PTM_Rejected` (if rejected)

#### **PTM_Accepted**
- **Purpose**: Execute accepted trade
- **Actions**: Transfer properties and cash
- **Next State**: `PTM_UpdateHold`

#### **PTM_Rejected**
- **Purpose**: Handle rejected trade
- **Next State**: `PTM_TradeEnd`

#### **PTM_UpdateHold**
- **Purpose**: Update holdings after trade
- **Next State**: `PTM_TradeEnd`

#### **PTM_NoTrade**
- **Purpose**: No viable trades available
- **Next State**: `PTM_TradeEnd`

#### **PTM_TradeEnd**
- **Purpose**: Complete trading phase
- **Next State**: `PTM_ImprovementCheck` (loop back)

### 6.3 End States

#### **PTM_End**
- **Purpose**: No more improvements to make
- **Next State**: `PTM_Exit`

#### **PTM_Exit**
- **Purpose**: Exit post-turn management
- **Next State**: `DoubleCheck`

## Decision Points Summary

The AI needs to make strategic decisions at these key states:

1. **🤖 EvaluateReleaseOptions**: How to get out of jail
2. **🤖 LD_EvalLiquidity**: Whether to buy a property
3. **🤖 LD_Mortgage**: Which properties to mortgage when short on cash
4. **🤖 PTM_EvalROI**: Whether and where to build houses/hotels
5. **🤖 PTM_FindPartner**: Who to trade with
6. **🤖 PTM_MakeOffer**: What trade to propose

## State Flow Diagram

```
AI_Turn
  └─> SenseState
       └─> JailCheck
            ├─> [In Jail] JailDecision -> EvaluateReleaseOptions -> ...
            └─> [Not in Jail] DiceRoll
                 └─> MoveToken
                      └─> LandingDecision
                           ├─> [Property] LD_PropertyCheck -> ...
                           ├─> [Tax] LD_TaxBranch -> ...
                           └─> [Special] LD_Special -> ...
                                └─> PostTurnManagement
                                     └─> PTM_ImprovementCheck
                                          ├─> [Build] PTM_BuildBranch -> ...
                                          ├─> [Trade] PTM_TradeBranch -> ...
                                          └─> PTM_End
                                               └─> DoubleCheck
                                                    └─> TurnEnd
```

## Implementation Notes

- States marked with 🤖 are where the OpenAI integration makes decisions
- Each state has clear entry/exit conditions
- The state machine is designed to handle all game scenarios
- States can loop back (e.g., building multiple properties)
- Error handling ensures graceful degradation if AI fails