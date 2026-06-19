WORKFLOW_OPTIMIZE_PROMPT = """You are building a Graph and corresponding Prompt to jointly solve {type} problems.
Referring to the given graph and prompt, which forms a basic example of a {type} solution approach,
please reconstruct and optimize them. You can add, modify, or delete nodes, parameters, or prompts. Include your
single modification in XML tags in your reply. Ensure they are complete and correct to avoid runtime failures. When
optimizing, you can incorporate critical thinking methods like review, revise, ensemble (generating multiple answers through different/similar prompts, then voting/integrating/checking the majority to obtain a final answer), selfAsk, etc. Consider
Python's loops (for, while, list comprehensions), conditional statements (if-elif-else, ternary operators),
or machine learning techniques (e.g., linear regression, decision trees, neural networks, clustering). The graph
complexity should not exceed 10. Use logical and control flow (IF-ELSE, loops) for a more enhanced graphical
representation.Ensure that all the prompts required by the current graph from prompt_custom are included.Exclude any other prompts.
Output the modified graph and all the necessary Prompts in prompt_custom (if needed).
The prompt you need to generate is only the one used in `prompt_custom.XXX` within Custom. Other methods already have built-in prompts and are prohibited from being generated. Only generate those needed for use in `prompt_custom`; please remove any unused prompts in prompt_custom.
the generated prompt must not contain any placeholders.
Considering information loss, complex graphs may yield better results, but insufficient information transmission can omit the solution. It's crucial to include necessary context during the process."""


WORKFLOW_INPUT = """
Here is a graph and the corresponding prompt (prompt only related to the custom method) that performed excellently in a previous iteration (maximum score is 1). You must make further optimizations and improvements based on this graph. The modified graph must differ from the provided example, and the specific differences should be noted within the <modification>xxx</modification> section.\n
<sample>
    <experience>{experience}</experience>
    <modification>(such as:add /delete /modify/ ...)</modification>
    <score>{score}</score>
    <graph>{graph}</graph>
    <prompt>{prompt}</prompt>(only prompt_custom)
    <operator_description>{operator_description}</operator_description>
</sample>
Below are the logs of some results with the aforementioned Graph that performed well but encountered errors, which can be used as references for optimization:
{log}

First, provide optimization ideas. **Only one detail point can be modified at a time**, and no more than 5 lines of code may be changed per modification—extensive modifications are strictly prohibited to maintain project focus!
When introducing new functionalities in the graph, please make sure to import the necessary libraries or modules yourself, except for operator, prompt_custom, create_llm_instance, and CostManage, which have already been automatically imported.
**Under no circumstances should Graph output None for any field.**
Use custom methods to restrict your output format, rather than using code (outside of the code, the system will extract answers based on certain rules and score them).
It is very important to format the Graph output answers, you can refer to the standard answer format in the log.
You do not need to manually import prompt_custom or operator to use them; they are already included in the execution environment.
"""

WORKFLOW_CUSTOM_USE = """\nHere's an example of using the `custom` method in graph:
```
# You can write your own prompt in <prompt>prompt_custom</prompt> and then use it in the Custom method in the graph
response = await self.custom(input=problem, instruction=prompt_custom.XXX_PROMPT)
# You can also concatenate previously generated string results in the input to provide more comprehensive contextual information.
# response = await self.custom(input=problem+f"xxx:{xxx}, xxx:{xxx}", instruction=prompt_custom.XXX_PROMPT)
# The output from the Custom method can be placed anywhere you need it, as shown in the example below
solution = await self.generate(problem=f"question:{problem}, xxx:{response['response']}")
```
Note: In custom, the input and instruction are directly concatenated(instruction+input), and placeholders are not supported. Please ensure to add comments and handle the concatenation externally.\n

**Introducing multiple operators at appropriate points can enhance performance. If you find that some provided operators are not yet used in the graph, try incorporating them.**
"""

WORKFLOW_TEMPLATE = """from typing import Literal
import {dataset}.workflows.template.operator as operator
import {dataset}.workflows.round_{round}.prompt as prompt_custom
from scripts.async_llm import create_llm_instance


from scripts.evaluator import DatasetType

{graph}
"""

WORKFLOW_MAS_OPTIMIZE_PROMPT = """You are building a Graph and corresponding Prompt to jointly solve {type} problems using multi-agent system (MAS) operators.
Referring to the given graph and prompt, which forms a basic example of a {type} solution approach,
please reconstruct and optimize them. You can add, modify, or delete nodes, parameters, or prompts. Include your
single modification in XML tags in your reply. Ensure they are complete and correct to avoid runtime failures.
The available operators are multi-agent topologies: Sequential, Star, SharedMemory, Debate, StarWithCoordinator, DebateWithModerator.
Each operator takes self.llm (worker) and self.aggregator_llm (aggregator/coordinator/moderator) as LLMs — do NOT create or reference other LLMs.
You can combine operators, chain them, or adjust their parameters (num_agents, n_rounds, prompts) to improve performance.
The graph complexity should not exceed 10 operator invocations.
Use logical and control flow (IF-ELSE, loops) for enhanced graph design.
Ensure that all prompts required by the current graph from prompt_custom are included. Exclude any unused prompts.
Output the modified graph and all necessary prompts in prompt_custom (if needed).
The generated prompt must not contain any placeholders other than the ones supported by the operators.
Considering information loss, complex graphs may yield better results, but insufficient information transmission can omit the solution. It's crucial to include necessary context during the process."""

WORKFLOW_MAS_USE = """\nHere are examples of using the MAS operators in the graph:
```
# Sequential: linear pipeline, each step gets the previous output
seq = operator.Sequential(llm=self.llm, num_rounds=2, prompts=["Solve: {problem}", "Review and improve: {previous_output}"])
result = await seq(problem)

# Star: parallel workers then aggregation
star = operator.Star(worker_llm=self.llm, aggregator_llm=self.aggregator_llm, num_agents=3,
    worker_prompts=["Solve this: {problem}"] * 3,
    aggregator_prompt="Given these solutions:\n{worker_outputs}\nPick the best for: {problem}")
result = await star(problem)

# Debate: agents debate then aggregation
debate = operator.Debate(worker_llm=self.llm, aggregator_llm=self.aggregator_llm, num_agents=3,
    worker_prompts=["Solve: {problem}\nOther proposals: {all_proposals}"] * 3,
    aggregator_prompt="Final answer for {problem} given: {all_proposals}", n_rounds=2)
result = await debate(problem)

# All MAS operators return dict with key 'response'
answer = result['response']
```
The available LLMs are self.llm (worker) and self.aggregator_llm (aggregator/coordinator/moderator).

Supported placeholders per operator:
- Sequential: {problem}, {previous_output}
- Star: worker_prompts use {problem}; aggregator_prompt uses {problem}, {worker_outputs}
- SharedMemory: worker_prompts use {problem}, {document}, {agent_id}, {round}; aggregator_prompt uses {problem}, {document}
- Debate: worker_prompts use {problem}, {all_proposals}, {round}, {agent_id}; aggregator_prompt uses {problem}, {all_proposals}
- StarWithCoordinator: worker_prompts use {problem}, {directive}, {round}, {agent_id}; coordinator_prompt uses {problem}, {worker_outputs}, {round}, {is_final}
- DebateWithModerator: agent_prompts use {problem}, {all_proposals}, {moderator_input}, {round}, {agent_id}; moderator_prompt uses {problem}, {all_proposals}, {round}, {is_final}

You can also define custom prompts in prompt_custom and reference them.

**Combining multiple operators or chaining them can enhance performance. Try different topologies.**
"""

WORKFLOW_MAS_TEMPLATE = """from typing import Literal
import {dataset}.workflows.template.operator as operator
import {dataset}.workflows.round_{round}.prompt as prompt_custom
from scripts.async_llm import create_llm_instance


from scripts.evaluator import DatasetType

{graph}
"""
