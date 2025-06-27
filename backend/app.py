from flask import Flask, jsonify, request
from flask_cors import CORS
import uuid
import os # For API Key check

# Langchain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
# from langchain.chains import LLMChain # Old way, new way is llm | prompt | parser

app = Flask(__name__)
CORS(app)

agents_db = {}
connections_db = {}

# --- Helper Functions ---
def generate_unique_id():
    return str(uuid.uuid4())

# --- Default configurations for new agent types ---
DEFAULT_CONFIGS = {
    "InputNode": {"value": {"text": "Default input text"}}, # Expects a dictionary
    "OutputNode": {},
    "ProcessingNode": {"prepend": "Processed: ", "append": ""}, # Old simulation node
    "PromptTemplateNode": {"template_string": "Translate the following text to French: {text}"},
    "GeminiLLMNode": {"model_name": "gemini-pro", "temperature": 0.7},
}

# --- API Endpoints ---
@app.route('/api/agents', methods=['POST'])
def create_agent():
    data = request.get_json()
    if not data or 'name' not in data or 'type' not in data:
        return jsonify({"error": "Missing name or type"}), 400

    agent_id = generate_unique_id()
    agent_type = data["type"]

    # Get default config for the agent type, or empty if not defined
    default_config = DEFAULT_CONFIGS.get(agent_type, {}).copy()
    # Merge with any config provided in the request, request takes precedence
    user_config = data.get("config", {})
    final_config = {**default_config, **user_config}

    new_agent = {
        "id": agent_id,
        "name": data["name"],
        "type": agent_type,
        "config": final_config,
        "position": data.get("position", {"x": 0, "y": 0})
    }
    agents_db[agent_id] = new_agent
    return jsonify(new_agent), 201

@app.route('/api/agents', methods=['GET'])
def get_agents():
    return jsonify(list(agents_db.values())), 200

@app.route('/api/agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    if agent_id not in agents_db:
        return jsonify({"error": "Agent not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    agent = agents_db[agent_id]
    agent["name"] = data.get("name", agent["name"])
    # Type should generally not be updated after creation, but allow if provided
    agent["type"] = data.get("type", agent["type"])

    # Config update: take existing, update with provided, ensuring no stale default fields
    new_config_data = data.get("config")
    if new_config_data is not None: # Important: check for None, as {} is a valid config
        agent["config"] = new_config_data

    agent["position"] = data.get("position", agent["position"])

    agents_db[agent_id] = agent
    return jsonify(agent), 200

@app.route('/api/agents/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    if agent_id not in agents_db:
        return jsonify({"error": "Agent not found"}), 404

    conn_ids_to_delete = [
        conn_id for conn_id, conn in connections_db.items()
        if conn["source_agent_id"] == agent_id or conn["target_agent_id"] == agent_id
    ]
    for conn_id in conn_ids_to_delete:
        del connections_db[conn_id]

    del agents_db[agent_id]
    return jsonify({"message": "Agent and associated connections deleted"}), 200

@app.route('/api/connections', methods=['POST'])
def create_connection():
    data = request.get_json()
    if not data or not all(k in data for k in ["source_agent_id", "target_agent_id", "source_port", "target_port"]):
        return jsonify({"error": "Missing required connection fields"}), 400

    if data["source_agent_id"] not in agents_db or data["target_agent_id"] not in agents_db:
        return jsonify({"error": "Source or target agent not found"}), 404

    connection_id = generate_unique_id()
    new_connection = {
        "id": connection_id,
        "source_agent_id": data["source_agent_id"],
        "target_agent_id": data["target_agent_id"],
        "source_port": data["source_port"], # For Langchain, these might be implicit (e.g. 'output' to 'input')
        "target_port": data["target_port"],
    }
    connections_db[connection_id] = new_connection
    return jsonify(new_connection), 201

@app.route('/api/connections', methods=['GET'])
def get_connections():
    return jsonify(list(connections_db.values())), 200

@app.route('/api/connections/<connection_id>', methods=['DELETE'])
def delete_connection(connection_id):
    if connection_id not in connections_db:
        return jsonify({"error": "Connection not found"}), 404
    del connections_db[connection_id]
    return jsonify({"message": "Connection deleted"}), 200


@app.route('/api/flow/run', methods=['POST'])
def run_flow():
    if not os.getenv("GOOGLE_API_KEY"):
        return jsonify({
            "error": "GOOGLE_API_KEY environment variable not set on the server.",
            "simulation_details": ["Error: GOOGLE_API_KEY not set."],
            "execution_order": [],
            "final_outputs": {}
        }), 500

    # 1. Build Execution Order (Simplified: find start, then follow connections)
    # This version assumes a linear chain for the Langchain part for simplicity:
    # InputNode -> PromptTemplateNode -> GeminiLLMNode -> OutputNode

    # Find the InputNode(s) - agents with no incoming connections or specifically typed 'InputNode'
    # Find the PromptTemplateNode, GeminiLLMNode, OutputNode by type.
    # This is a simplified approach for the specific Input -> Prompt -> LLM -> Output flow.
    # A more general solution would use proper topological sort and handle complex graphs.

    input_node_data = None
    prompt_template_node_data = None
    llm_node_data = None
    # output_node_data = None # Not strictly needed for execution, but for final display

    # Identify nodes by type for the specific flow
    # This is a simplification. A robust system would trace connections.
    for agent_id, agent in agents_db.items():
        if agent['type'] == 'InputNode':
            # For simplicity, assume one input node provides the initial data for the chain.
            # A more complex setup might gather inputs from multiple InputNodes or other sources.
            is_target = any(conn['target_agent_id'] == agent_id for conn in connections_db.values())
            if not is_target: # If it's not a target of any connection, it's a potential start
                 input_node_data = agent
                 # break # Take the first one for now

        elif agent['type'] == 'PromptTemplateNode':
            prompt_template_node_data = agent
        elif agent['type'] == 'GeminiLLMNode':
            llm_node_data = agent
        # elif agent['type'] == 'OutputNode':
        #     output_node_data = agent # Useful for knowing where the final result goes

    # Validate that we have the necessary components for our specific chain
    if not input_node_data:
        return jsonify({"error": "InputNode not found or not configured as a starting node in the flow.", "simulation_details": ["Error: InputNode missing."]}), 400
    if not prompt_template_node_data:
        return jsonify({"error": "PromptTemplateNode not found in the flow.", "simulation_details": ["Error: PromptTemplateNode missing."]}), 400
    if not llm_node_data:
        return jsonify({"error": "GeminiLLMNode not found in the flow.", "simulation_details": ["Error: GeminiLLMNode missing."]}), 400

    try:
        # 2. Get initial input from InputNode config
        # The 'value' in InputNode's config is expected to be a dictionary
        # which will serve as input variables for the prompt template.
        chain_input = input_node_data['config'].get('value', {})
        if not isinstance(chain_input, dict):
            return jsonify({"error": "InputNode 'value' config must be a dictionary (object).", "simulation_details": ["Error: InputNode 'value' not a dict."]}), 400


        # 3. Setup Langchain components
        # Prompt Template
        template_string = prompt_template_node_data['config'].get('template_string', '')
        if not template_string:
            return jsonify({"error": "PromptTemplateNode has no template_string configured."}), 400

        prompt = PromptTemplate.from_template(template_string)

        # LLM
        llm_config = llm_node_data['config']
        llm = ChatGoogleGenerativeAI(
            model=llm_config.get('model_name', 'gemini-pro'),
            temperature=float(llm_config.get('temperature', 0.7)),
            # GOOGLE_API_KEY is picked up from environment by the library
        )

        # Output Parser (optional, but good practice)
        output_parser = StrOutputParser()

        # 4. Construct and run the chain (LCEL - Langchain Expression Language)
        # chain = LLMChain(llm=llm, prompt=prompt) # Old way
        chain = prompt | llm | output_parser # New LCEL way

        # Execute the chain
        # The input to `chain.invoke` should be a dictionary if the prompt expects multiple variables.
        # If the prompt expects a single variable (e.g. "input"), and chain_input is just that value,
        # Langchain might handle it, but it's safer to match the prompt's input_variables.
        # For from_template, it infers input_variables.

        # Example: if template is "Question: {question}\nAnswer:"
        # chain_input should be {"question": "What is the capital of France?"}

        response = chain.invoke(chain_input)

        # 5. Return the result
        return jsonify({
            "message": "Langchain flow executed successfully.",
            "execution_order": [input_node_data['id'], prompt_template_node_data['id'], llm_node_data['id']], # Simplified
            "simulation_details": [
                f"Input: {chain_input}",
                f"Prompt Used: {template_string}",
                f"LLM Model: {llm_config.get('model_name')}",
                f"LLM Response: {response}"
            ],
            "final_outputs": {llm_node_data['id']: response} # Output of the LLM node
        }), 200

    except Exception as e:
        print(f"Error during Langchain flow execution: {e}")
        return jsonify({
            "error": f"Langchain execution failed: {str(e)}",
            "simulation_details": [f"Error: {str(e)}"],
            "execution_order": [],
            "final_outputs": {}
        }), 500

if __name__ == '__main__':
    print("--- Langflow MVP Backend ---")
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY environment variable is not set.")
        print("The Langchain Gemini LLM node will not work without it.")
    print("--------------------------")
    app.run(debug=True, port=5001)
