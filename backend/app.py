from flask import Flask, jsonify, request
from flask_cors import CORS
import uuid

# Create Flask app instance
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage for agents and connections
# For a real application, you would use a database.
agents_db = {}  # Stores AgentNode objects, keyed by agent_id
connections_db = {} # Stores Connection objects, keyed by a unique connection_id

# --- Data Models (as Python dictionaries for simplicity in MVP) ---
# AgentNode: {'id': str, 'name': str, 'type': str, 'config': dict, 'position': {'x': int, 'y': int}}
# Connection: {'id': str, 'source_agent_id': str, 'target_agent_id': str, 'source_port': str, 'target_port': str}

# --- Helper Functions ---
def generate_unique_id():
    return str(uuid.uuid4())

# --- API Endpoints ---

# Agent Endpoints
@app.route('/api/agents', methods=['POST'])
def create_agent():
    data = request.get_json()
    if not data or 'name' not in data or 'type' not in data:
        return jsonify({"error": "Missing name or type"}), 400

    agent_id = generate_unique_id()
    new_agent = {
        "id": agent_id,
        "name": data["name"],
        "type": data["type"],
        "config": data.get("config", {}),
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
    agent["type"] = data.get("type", agent["type"])
    agent["config"] = data.get("config", agent["config"])
    agent["position"] = data.get("position", agent["position"])

    agents_db[agent_id] = agent
    return jsonify(agent), 200

@app.route('/api/agents/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    if agent_id not in agents_db:
        return jsonify({"error": "Agent not found"}), 404

    # Also remove connections associated with this agent
    conn_ids_to_delete = [
        conn_id for conn_id, conn in connections_db.items()
        if conn["source_agent_id"] == agent_id or conn["target_agent_id"] == agent_id
    ]
    for conn_id in conn_ids_to_delete:
        del connections_db[conn_id]

    del agents_db[agent_id]
    return jsonify({"message": "Agent and associated connections deleted"}), 200

# Connection Endpoints
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
        "source_port": data["source_port"],
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

# Flow Execution Endpoint (Placeholder for MVP)
@app.route('/api/flow/run', methods=['POST'])
def run_flow():
    # For MVP, this will just log the current state or a simple message.
    # In a real app, this would involve topological sort and agent execution.
    current_agents = list(agents_db.values())
    current_connections = list(connections_db.values())

    print("--- Running Flow ---")
    print(f"Agents: {current_agents}")
    print(f"Connections: {current_connections}")
    print("--------------------")

    # Basic execution simulation (very simplified)
    # Find input nodes (nodes with no incoming connections from other agents in the flow)
    # This is a naive approach for MVP. A proper solution needs topological sort.

    output_messages = []

    # Identify potential starting nodes (those not targeted by any connection)
    target_agent_ids_in_connections = {conn['target_agent_id'] for conn in current_connections}

    execution_order = [] # This will store agent_ids in a rough order

    # Simple topological sort (iterative removal of nodes with no incoming edges from remaining nodes)
    # This is a more robust way than just finding nodes with no incoming connections at all,
    # as it handles chains of agents.

    # Create a copy of agents and connections to manipulate for sorting
    temp_agents = {agent_id: agent for agent_id, agent in agents_db.items()}
    temp_connections = list(connections_db.values())

    while len(temp_agents) > 0:
        # Find nodes with no incoming connections *from other agents still in temp_agents*
        current_target_ids = {conn['target_agent_id'] for conn in temp_connections}

        # Nodes that are not targets OR are of type 'input' (can start a flow)
        # Or nodes whose source for incoming connections have already been processed (not handled in this simplified version)
        start_nodes_ids = [
            agent_id for agent_id, agent_data in temp_agents.items()
            if agent_id not in current_target_ids or agent_data.get('type', '').lower() == 'input'
        ]

        if not start_nodes_ids:
            if temp_agents: # If there are agents left but no start nodes, there's a cycle or disconnected graph
                output_messages.append(f"Error: Cycle detected or disconnected components in the graph. Remaining agents: {list(temp_agents.keys())}")
                break
            break # All nodes processed

        # Add found start nodes to execution order and remove them for next iteration
        for agent_id in start_nodes_ids:
            if agent_id in temp_agents: # Ensure it hasn't been processed in a previous step of this iteration (e.g. multiple inputs)
                execution_order.append(agent_id)
                # Remove connections originating from this agent to correctly find next start_nodes
                temp_connections = [conn for conn in temp_connections if conn['source_agent_id'] != agent_id]
                del temp_agents[agent_id]

        # The break condition for cycles/no progress is already effectively handled by the
        # 'if not start_nodes_ids:' check at the beginning of the while loop.
        # If that check leads to a break and temp_agents is still populated,
        # it implies a cycle or disconnected components that are not inputs.

    simulated_output = f"Simulated execution order: {execution_order}\n"

    # Simulate message passing
    agent_outputs = {} # To store output of each agent

    for agent_id in execution_order:
        agent = agents_db.get(agent_id)
        if not agent:
            continue

        # Gather inputs for the current agent
        incoming_message = ""
        # Find connections where this agent is the target
        for conn in current_connections:
            if conn['target_agent_id'] == agent_id:
                source_agent_output = agent_outputs.get(conn['source_agent_id'])
                if source_agent_output: # Check if source agent has produced output
                    # In a real system, you'd handle specific ports (source_port, target_port)
                    incoming_message += str(source_agent_output) + " "

        incoming_message = incoming_message.strip()

        message = f"Agent '{agent['name']}' (ID: {agent_id}, Type: {agent['type']}):\n"
        config_str = str(agent.get('config', {}))

        if agent['type'].lower() == 'input':
            # Input agents generate a message, possibly from config
            current_output = agent.get('config', {}).get('message', f"Input from {agent['name']}")
            message += f"  - Generates: '{current_output}' (config: {config_str})\n"
            agent_outputs[agent_id] = current_output
        elif agent['type'].lower() == 'processing':
            # Processing agents transform the message
            prepend = agent.get('config', {}).get('prepend', '')
            append = agent.get('config', {}).get('append', '')
            current_output = f"{prepend} {incoming_message} {append}".strip()
            message += f"  - Received: '{incoming_message}'\n"
            message += f"  - Processes to: '{current_output}' (config: {config_str})\n"
            agent_outputs[agent_id] = current_output
        elif agent['type'].lower() == 'output':
            # Output agents display the message
            message += f"  - Final Output: '{incoming_message}' (config: {config_str})\n"
            agent_outputs[agent_id] = incoming_message # It might also pass through its input
        else:
            # Default behavior for unknown types
            message += f"  - Received: '{incoming_message}'\n"
            message += f"  - No specific action, passing through. (config: {config_str})\n"
            agent_outputs[agent_id] = incoming_message

        simulated_output += message

    output_messages.append(simulated_output)

    return jsonify({
        "message": "Flow run simulated. Check server logs for details.",
        "simulation_details": output_messages,
        "execution_order": execution_order,
        "final_outputs": agent_outputs # Output of all agents in the flow
    }), 200


if __name__ == '__main__':
    # Note: For development, Flask's built-in server is fine.
    # For production, use a proper WSGI server like Gunicorn.
    app.run(debug=True, port=5001) # Using port 5001 to avoid potential conflicts
