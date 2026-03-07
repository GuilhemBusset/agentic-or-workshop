# Instructor Guide: LLM Architecture Primer (Single-Graph Autoregressive Flow)

## File
- `00-llm-architecture-primer.html`

## Teaching Objective
Use one evolving graph to explain how a large language model (LLM) transforms prompt text into generated output through an autoregressive loop.

## Learning
- LLM generation is autoregressive: one token is produced at a time, then appended, then repeated.
- Attention and the feed-forward network (`FFN`) are distinct sub-steps in the decode path.
- `MoE` changes FFN routing behavior, not core attention equations.
- `RAG` injects external context before tokenization/prefill in this teaching model.
- `Memory` and `Tool` are optional return paths that can influence late-stage generation.
- Word-like input is turned into numeric representations, then back to token choices.

## Core Terms
- **Token**: a text chunk the model processes.
- **Token ID**: numeric code for a token.
- **Key/Value (KV) cache**: stored key/value vectors from past tokens used by attention.
- **Query/Key/Value (Q/K/V)**: vectors used to compute what the current token attends to and what content gets transferred.
- **Logits**: numeric scores for all possible next tokens.
- **Sampling**: choosing the next token from those scores.
- **Autoregressive loop**: append one token, update state, repeat.

## Execution Stages
1. **Prompt + System Context**
- What is happening: The model receives instructions (system message), the user request, and optional retrieved notes, then places them in one ordered context.
- Why this matters: If context order is wrong or missing, the model can misunderstand the task before it even starts computing.

2. **Tokenize Input**
- What is happening: Text is split into tokens, and each token is converted into a number (token ID).
- Why this matters: The model can only do math on numbers, so this is the bridge from language to computation.

3. **Prefill Transformer (build KV cache)**
- What is happening: The model reads the full input once and stores reusable Key/Value vectors in cache.
- Why this matters: This gives the model memory of the prompt and makes next-token generation much faster.
- Note: the embedding lookup (token ID → dense vector) is folded into the Prefill step for simplicity.

4. **Start Decode Step (current position)**
- What is happening: The model opens the next position where one new token will be generated.
- Why this matters: Generation is one-step-at-a-time, so this sets the exact place for the next decision.

5. **Compute Attention (Q vs cached K/V)**
- What is happening: The current query compares itself with cached keys and pulls relevant values.
- Why this matters: This is how the model focuses on the most useful earlier information instead of treating all past text equally.

6. **Run MLP + Residual Update**
- What is happening: The attended signal goes through a transformation block (dense FFN or MoE experts), then is merged into the running hidden state.
- Why this matters: Attention finds relevant info; this step refines that info into a stronger prediction state.

7. **Project to Logits**
- What is happening: The hidden state is converted into a score for every possible next token.
- Why this matters: These scores are the model's raw preference signal before picking a token.

8. **Sample / Select Next Token**
- What is happening: A decoding rule selects one token from the scored candidates.
- Why this matters: This turns model preference into an actual output choice.

9. **Append Token + Update KV Cache**
- What is happening: The chosen token is appended to the output and its state is added to cache.
- Why this matters: The new token becomes part of history, so the next step can build on it.

10. **Stop or Repeat Loop**
- What is happening: The system checks stopping criteria (for example length or end token); if not met, it loops back for another token.
- Why this matters: This control logic determines whether the model keeps generating or returns the final answer.

## Important Clarification
This is a pedagogical system model, not a vendor-specific architecture claim.
- Real deployments may retrieve at different times.
- Tool execution can be external orchestration.
- Memory mechanisms vary widely across systems.

## Common Misconceptions To Correct
- “LLMs output whole sentences at once.” (They output one token per loop step.)
- “MoE changes attention math.” (MoE changes FFN routing path.)
- “RAG is always after generation.” (In this teaching model, RAG grounds context before tokenization. In practice, retrieval timing varies — it can happen before, during, or after generation depending on the system.)
- “Sampling is random guessing.” (It is constrained by logits/probabilities.)

## Anticipated Questions
- **”Why is there only one Attention node?”** Real transformer models use multi-head attention, where several parallel attention heads each learn different patterns. This diagram flattens them into a single node for clarity.
- **”Why is there only one layer?”** Real transformers stack N identical Attention → MLP blocks (e.g., 32 layers in a 7B model, 80+ in larger ones). This diagram shows one conceptual pass through the layer to keep the flow readable.

## Additional Information
- LLM Visualization: https://bbycroft.net/llm
- Interpretability Platform: https://www.neuronpedia.org/