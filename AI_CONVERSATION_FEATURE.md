# AI-to-AI Conversation Feature

## Overview
This feature allows AIs to communicate with each other before making important decisions in the Monopoly game. When faced with a decision, an AI can choose to initiate a conversation with the other AI player(s) to discuss strategy, negotiate, or gather information.

## How It Works

### 1. Decision Option
When an AI is presented with a decision, a new option `talk_to_other_ai` is automatically added to the available choices. The AI can choose this option to start a conversation.

### 2. Conversation Flow
- The AI can choose `talk_to_other_ai` multiple times (up to 3 conversation rounds)
- Each conversation consists of 2-4 exchanges between the AIs
- After each conversation, the AI decides whether to:
  - Continue talking (returns `talk_to_other_ai` again)
  - Make a final decision (returns one of the original options)

### 3. Conversation Management
```python
# While loop handles multiple conversation rounds
while result['decision'].lower() == 'talk_to_other_ai' and conversation_count < max_conversations:
    conversation_count += 1
    # Initiate conversation
    conversation_result = self._initiate_ai_conversation(...)
    
    # Check if AI wants to continue talking or make a decision
    if conversation_result['decision'].lower() != 'talk_to_other_ai':
        return conversation_result
```

### 4. Dynamic Probability
The probability of continuing conversations decreases with each round:
- Round 1: 70% chance to continue talking
- Round 2: 50% chance to continue talking  
- Round 3: 30% chance to continue talking

## Example Conversation

```
[AI Chat] GPT1: "Hé Claude, j'aimerais discuter avant de prendre ma décision. Je pense qu'acheter cette propriété pourrait être stratégique."

[AI Chat] Claude: "Intéressant... Cette propriété complèterait mon monopole rouge. Qu'est-ce que tu proposes?"

[AI Chat] GPT1: "Je pourrais te la laisser si tu me donnes une compensation intéressante plus tard."

[AI Chat] Claude: "Je garde ça en tête, mais je préfère voir comment la partie évolue d'abord."

[AI Chat] GPT1: "Bon, après cette discussion enrichissante, voici ma décision..."
```

## Benefits

1. **Strategic Depth**: AIs can negotiate and form temporary alliances
2. **Realistic Gameplay**: Mimics human player interactions
3. **Dynamic Decisions**: Decisions can be influenced by conversations
4. **Entertainment**: Creates interesting dialogue for observers

## Configuration

The feature is automatically enabled for all AI players. No configuration needed.

### Limits
- Maximum 3 conversation rounds per decision
- Each conversation has 2-4 exchanges
- Timeout protection prevents infinite loops

## Technical Implementation

### Key Methods

1. **make_decision()**: Main decision method with conversation loop
2. **_initiate_ai_conversation()**: Manages a single conversation round
3. **_generate_ai_response()**: Generates contextual AI responses
4. **_make_final_decision_after_conversation()**: Makes decision with conversation context

### AI Prompts
AIs are instructed to:
- Be strategic but diplomatic
- Keep responses concise (max 2 sentences)
- Consider their own interests
- Use conversation history in final decisions

## Monitoring

All conversations are sent to the AI Chat Monitor (port 8003) with:
- Timestamp
- From/To players
- Message content
- Conversation context

## Future Enhancements

- Multi-player conversations (3+ players)
- Topic-specific conversations (trades, alliances)
- Persistent conversation memory across turns
- Conversation-based achievements