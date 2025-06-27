document.addEventListener('DOMContentLoaded', () => {
    const apiUrl = 'http://localhost:5001/api'; // Backend API URL

    // DOM Elements
    const canvas = document.getElementById('canvas');
    const sidebarAgentTypes = document.querySelectorAll('.agent-type');
    const propertiesPanel = document.getElementById('propertiesPanel');
    const runFlowButton = document.getElementById('runFlowButton');
    const flowOutputContent = document.getElementById('flowOutputContent');

    // State
    let agents = {}; // Use an object for faster lookups by ID
    let connections = {}; // Use an object for faster lookups by ID
    let selectedAgentId = null;
    let currentlyDraggedAgent = null;
    let dragOffsetX, dragOffsetY;

    // For drawing connections
    let isDrawingConnection = false;
    let connectionStartAgentId = null;
    let connectionStartPortType = null; // 'input' or 'output'
    let tempLine = null; // SVG line element for preview

    // --- Initialization ---
    loadInitialData();

    // --- API Helper Functions ---
    async function apiGet(endpoint) {
        const response = await fetch(`${apiUrl}/${endpoint}`);
        if (!response.ok) throw new Error(`API GET ${endpoint} failed: ${response.statusText}`);
        return response.json();
    }

    async function apiPost(endpoint, body) {
        const response = await fetch(`${apiUrl}/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) throw new Error(`API POST ${endpoint} failed: ${response.statusText}`);
        return response.json();
    }

    async function apiPut(endpoint, body) {
        const response = await fetch(`${apiUrl}/${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) throw new Error(`API PUT ${endpoint} failed: ${response.statusText}`);
        return response.json();
    }

    async function apiDelete(endpoint) {
        const response = await fetch(`${apiUrl}/${endpoint}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(`API DELETE ${endpoint} failed: ${response.statusText}`);
        return response.json();
    }

    // --- Load Initial Data ---
    async function loadInitialData() {
        try {
            const [agentsData, connectionsData] = await Promise.all([
                apiGet('agents'),
                apiGet('connections')
            ]);
            agentsData.forEach(agent => agents[agent.id] = agent);
            connectionsData.forEach(conn => connections[conn.id] = conn);
            renderAll();
        } catch (error) {
            console.error("Error loading initial data:", error);
            flowOutputContent.textContent = `Error loading initial data: ${error.message}`;
        }
    }

    // --- Rendering Functions ---
    function renderAll() {
        renderAgents();
        renderConnections();
        if (selectedAgentId && agents[selectedAgentId]) {
            renderPropertiesPanel(agents[selectedAgentId]);
        } else {
            clearPropertiesPanel();
        }
    }

    function renderAgents() {
        canvas.querySelectorAll('.agent-node').forEach(node => node.remove()); // Clear existing
        Object.values(agents).forEach(agent => {
            const agentDiv = document.createElement('div');
            agentDiv.className = 'agent-node';
            agentDiv.id = `agent-${agent.id}`;
            agentDiv.style.left = `${agent.position.x}px`;
            agentDiv.style.top = `${agent.position.y}px`;
            if (agent.id === selectedAgentId) {
                agentDiv.classList.add('selected');
            }

            agentDiv.innerHTML = `
                <h4>${agent.name} (${agent.type})</h4>
                <div class="ports">
                    <div class="port input" data-agent-id="${agent.id}" data-port-type="input"></div>
                    <div class="port output" data-agent-id="${agent.id}" data-port-type="output"></div>
                </div>
            `;
            // Dragging existing agent
            agentDiv.addEventListener('mousedown', (e) => {
                if (e.target.classList.contains('port')) return; // Don't drag if clicking on port
                e.preventDefault();
                selectAgent(agent.id);
                currentlyDraggedAgent = agentDiv;
                const rect = agentDiv.getBoundingClientRect();
                const canvasRect = canvas.getBoundingClientRect();
                dragOffsetX = e.clientX - rect.left;
                dragOffsetY = e.clientY - rect.top;
                document.addEventListener('mousemove', onAgentDrag);
                document.addEventListener('mouseup', onAgentDragEnd);
            });

            // Port click for connections
            agentDiv.querySelectorAll('.port').forEach(port => {
                port.addEventListener('click', (e) => handlePortClick(e, agent.id, port.dataset.portType));
            });

            canvas.appendChild(agentDiv);
        });
    }

    function renderConnections() {
        let svgLines = document.getElementById('connection-lines');
        if (!svgLines) {
            svgLines = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svgLines.id = 'connection-lines';
            canvas.appendChild(svgLines);
        }
        svgLines.innerHTML = ''; // Clear existing lines

        Object.values(connections).forEach(conn => {
            const sourceAgent = agents[conn.source_agent_id];
            const targetAgent = agents[conn.target_agent_id];
            if (!sourceAgent || !targetAgent) return;

            const sourceElem = document.getElementById(`agent-${sourceAgent.id}`);
            const targetElem = document.getElementById(`agent-${targetAgent.id}`);
            if (!sourceElem || !targetElem) return;

            // Find port elements (assuming one input and one output port for simplicity)
            const sourcePortElem = sourceElem.querySelector('.port.output');
            const targetPortElem = targetElem.querySelector('.port.input');

            if (!sourcePortElem || !targetPortElem) return;

            const line = createSvgLine(sourcePortElem, targetPortElem, conn.id);
            svgLines.appendChild(line);
        });
    }

    function createSvgLine(sourcePortElem, targetPortElem, connectionId) {
        const canvasRect = canvas.getBoundingClientRect();

        const sourceRect = sourcePortElem.getBoundingClientRect();
        const targetRect = targetPortElem.getBoundingClientRect();

        // Calculate port centers relative to the canvas
        // Port center X = port.left - canvas.left + port.width / 2
        // Port center Y = port.top - canvas.top + port.height / 2
        const x1 = sourceRect.left - canvasRect.left + sourceRect.width / 2 + canvas.scrollLeft;
        const y1 = sourceRect.top - canvasRect.top + sourceRect.height / 2 + canvas.scrollTop;
        const x2 = targetRect.left - canvasRect.left + targetRect.width / 2 + canvas.scrollLeft;
        const y2 = targetRect.top - canvasRect.top + targetRect.height / 2 + canvas.scrollTop;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', '#333');
        line.setAttribute('stroke-width', '2');
        if (connectionId) {
            line.dataset.connectionId = connectionId; // Store connection ID for potential interaction
        }
        return line;
    }


    function renderPropertiesPanel(agent) {
        propertiesPanel.innerHTML = `
            <h3>Edit: ${agent.name}</h3>
            <input type="hidden" id="agentId" value="${agent.id}">
            <div>
                <label for="agentName">Name:</label>
                <input type="text" id="agentName" value="${agent.name}">
            </div>
            <div>
                <label for="agentTypeDisplay">Type:</label>
                <input type="text" id="agentTypeDisplay" value="${agent.type}" disabled>
            </div>
            <h4>Configuration:</h4>
            <div id="agentConfigFields">
                ${Object.entries(agent.config || {}).map(([key, value]) => `
                    <div>
                        <label for="config-${key}">${key}:</label>
                        <textarea id="config-${key}" data-key="${key}" rows="2">${value}</textarea>
                    </div>
                `).join('')}
                 ${agent.type === 'input' && !agent.config.message ? '<div><label for="config-message">message:</label><textarea id="config-message" data-key="message" rows="2"></textarea></div>' : ''}
                 ${agent.type === 'processing' && !agent.config.prepend ? '<div><label for="config-prepend">prepend:</label><textarea id="config-prepend" data-key="prepend" rows="2"></textarea></div>' : ''}
                 ${agent.type === 'processing' && !agent.config.append ? '<div><label for="config-append">append:</label><textarea id="config-append" data-key="append" rows="2"></textarea></div>' : ''}
            </div>
            <button id="saveAgentButton">Save Changes</button>
            <button id="deleteAgentButton" style="background-color: #e74c3c;">Delete Agent</button>
        `;

        document.getElementById('saveAgentButton').addEventListener('click', saveAgentProperties);
        document.getElementById('deleteAgentButton').addEventListener('click', deleteSelectedAgent);
    }

    function clearPropertiesPanel() {
        propertiesPanel.innerHTML = '<p>Select an agent to see its properties.</p>';
        selectedAgentId = null;
        document.querySelectorAll('.agent-node.selected').forEach(n => n.classList.remove('selected'));
    }

    // --- Event Handlers ---

    // Dragging agent types from sidebar
    sidebarAgentTypes.forEach(typeElement => {
        typeElement.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', e.target.dataset.type);
            e.dataTransfer.effectAllowed = 'copy';
        });
    });

    canvas.addEventListener('dragover', (e) => {
        e.preventDefault(); // Allow drop
        e.dataTransfer.dropEffect = 'copy';
    });

    canvas.addEventListener('drop', async (e) => {
        e.preventDefault();
        const agentType = e.dataTransfer.getData('text/plain');
        const canvasRect = canvas.getBoundingClientRect();
        const x = e.clientX - canvasRect.left + canvas.scrollLeft;
        const y = e.clientY - canvasRect.top + canvas.scrollTop;

        const agentName = `${agentType.charAt(0).toUpperCase() + agentType.slice(1)} Node`;
        const newAgentData = {
            name: agentName,
            type: agentType,
            position: { x, y },
            config: agentType === 'input' ? { message: "Default input" } :
                    agentType === 'processing' ? { prepend: "", append: "" } : {}
        };

        try {
            const createdAgent = await apiPost('agents', newAgentData);
            agents[createdAgent.id] = createdAgent;
            selectAgent(createdAgent.id); // Select new agent
            renderAll();
        } catch (error) {
            console.error("Error creating agent:", error);
            flowOutputContent.textContent = `Error creating agent: ${error.message}`;
        }
    });

    // Moving existing agents on canvas
    function onAgentDrag(e) {
        if (!currentlyDraggedAgent || !selectedAgentId) return;
        const canvasRect = canvas.getBoundingClientRect();
        let newX = e.clientX - canvasRect.left - dragOffsetX + canvas.scrollLeft;
        let newY = e.clientY - canvasRect.top - dragOffsetY + canvas.scrollTop;

        // Optional: Snap to grid or constrain to canvas boundaries
        newX = Math.max(0, newX); // Prevent dragging outside left
        newY = Math.max(0, newY); // Prevent dragging outside top
        // newX = Math.min(newX, canvas.scrollWidth - currentlyDraggedAgent.offsetWidth);
        // newY = Math.min(newY, canvas.scrollHeight - currentlyDraggedAgent.offsetHeight);


        currentlyDraggedAgent.style.left = `${newX}px`;
        currentlyDraggedAgent.style.top = `${newY}px`;

        // Update connections visually while dragging
        renderConnections();
    }

    async function onAgentDragEnd(e) {
        if (!currentlyDraggedAgent || !selectedAgentId) return;
        document.removeEventListener('mousemove', onAgentDrag);
        document.removeEventListener('mouseup', onAgentDragEnd);

        const agent = agents[selectedAgentId];
        agent.position.x = parseInt(currentlyDraggedAgent.style.left, 10);
        agent.position.y = parseInt(currentlyDraggedAgent.style.top, 10);

        try {
            await apiPut(`agents/${agent.id}`, agent);
            // No need to re-render all if only position changed and connections are updated during drag
        } catch (error) {
            console.error("Error updating agent position:", error);
            flowOutputContent.textContent = `Error updating agent position: ${error.message}`;
            // Revert position if save failed? Or just re-render from server state.
            loadInitialData(); // Simplest way to ensure consistency
        }
        currentlyDraggedAgent = null;
    }

    // Agent selection
    function selectAgent(agentId) {
        if (selectedAgentId === agentId) return; // Already selected

        if (selectedAgentId && agents[selectedAgentId]) {
            document.getElementById(`agent-${selectedAgentId}`)?.classList.remove('selected');
        }
        selectedAgentId = agentId;
        const agentNode = document.getElementById(`agent-${agentId}`);
        agentNode?.classList.add('selected');
        renderPropertiesPanel(agents[agentId]);
    }

    // Canvas click to deselect
    canvas.addEventListener('click', (e) => {
        if (e.target === canvas || e.target.id === 'connection-lines') { // Clicked on canvas background or SVG container
             if (isDrawingConnection) { // If drawing a connection, cancel it
                isDrawingConnection = false;
                connectionStartAgentId = null;
                connectionStartPortType = null;
                if (tempLine) {
                    tempLine.remove();
                    tempLine = null;
                }
                renderConnections(); // Redraw to remove temp line if it was part of main SVG
            } else if (selectedAgentId) {
                clearPropertiesPanel();
            }
        }
    });


    // Properties panel actions
    async function saveAgentProperties() {
        if (!selectedAgentId) return;
        const agent = agents[selectedAgentId];
        const newName = document.getElementById('agentName').value;

        const updatedConfig = {};
        document.querySelectorAll('#agentConfigFields textarea').forEach(textarea => {
            updatedConfig[textarea.dataset.key] = textarea.value;
        });

        const updatedAgent = { ...agent, name: newName, config: updatedConfig };

        try {
            const savedAgent = await apiPut(`agents/${agent.id}`, updatedAgent);
            agents[savedAgent.id] = savedAgent;
            renderAll(); // Re-render to reflect name change and updated props
            // Optionally, provide user feedback e.g. "Saved!"
        } catch (error) {
            console.error("Error saving agent properties:", error);
            flowOutputContent.textContent = `Error saving agent: ${error.message}`;
        }
    }

    async function deleteSelectedAgent() {
        if (!selectedAgentId || !confirm(`Are you sure you want to delete agent "${agents[selectedAgentId].name}"?`)) return;

        try {
            await apiDelete(`agents/${selectedAgentId}`);
            delete agents[selectedAgentId];
            // Also remove connections associated with this agent from the frontend state
            Object.keys(connections).forEach(connId => {
                if (connections[connId].source_agent_id === selectedAgentId || connections[connId].target_agent_id === selectedAgentId) {
                    delete connections[connId];
                }
            });
            selectedAgentId = null;
            clearPropertiesPanel();
            renderAll();
        } catch (error) {
            console.error("Error deleting agent:", error);
            flowOutputContent.textContent = `Error deleting agent: ${error.message}`;
        }
    }

    // Connection drawing logic
    function handlePortClick(event, agentId, portType) {
        event.stopPropagation(); // Prevent agent selection or canvas click
        const agent = agents[agentId];
        if (!agent) return;

        if (!isDrawingConnection) {
            // Start drawing a new connection
            isDrawingConnection = true;
            connectionStartAgentId = agentId;
            connectionStartPortType = portType; // 'input' or 'output'

            // Create a temporary line for visual feedback
            if (!tempLine) {
                let svgLines = document.getElementById('connection-lines');
                if (!svgLines) { // Should exist, but defensive
                    svgLines = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    svgLines.id = 'connection-lines';
                    canvas.appendChild(svgLines);
                }
                tempLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                tempLine.setAttribute('stroke', '#777');
                tempLine.setAttribute('stroke-width', '2');
                tempLine.setAttribute('stroke-dasharray', '5,5'); // Dashed line for temp
                svgLines.appendChild(tempLine);
            }

            const portElem = event.target;
            const canvasRect = canvas.getBoundingClientRect();
            const portRect = portElem.getBoundingClientRect();
            const x1 = portRect.left - canvasRect.left + portRect.width / 2 + canvas.scrollLeft;
            const y1 = portRect.top - canvasRect.top + portRect.height / 2 + canvas.scrollTop;
            tempLine.setAttribute('x1', x1);
            tempLine.setAttribute('y1', y1);
            tempLine.setAttribute('x2', x1); // Initially, end at start point
            tempLine.setAttribute('y2', y1);
            tempLine.style.display = 'block';

            document.addEventListener('mousemove', onDrawingConnectionMouseMove);
            // Next click on a port will complete or cancel

        } else {
            // Finish drawing connection
            const connectionEndAgentId = agentId;
            const connectionEndPortType = portType;

            // Basic validation: cannot connect to self, cannot connect output to output, etc.
            if (connectionStartAgentId === connectionEndAgentId) {
                console.warn("Cannot connect agent to itself.");
            } else if (connectionStartPortType === connectionEndPortType) {
                console.warn(`Cannot connect ${connectionStartPortType} to ${connectionEndPortType}.`);
            } else {
                // Determine source and target based on port types
                let sourceAgent, targetAgent, sourcePort, targetPort;
                if (connectionStartPortType === 'output' && connectionEndPortType === 'input') {
                    sourceAgent = connectionStartAgentId;
                    targetAgent = connectionEndAgentId;
                    sourcePort = 'output'; // Assuming generic port names for now
                    targetPort = 'input';
                } else if (connectionStartPortType === 'input' && connectionEndPortType === 'output') {
                    sourceAgent = connectionEndAgentId;
                    targetAgent = connectionStartAgentId;
                    sourcePort = 'output';
                    targetPort = 'input';
                } else {
                    console.error("Invalid port connection logic.");
                    resetConnectionDrawingState();
                    return;
                }

                // Check if this connection already exists
                const existingConnection = Object.values(connections).find(c =>
                    c.source_agent_id === sourceAgent && c.target_agent_id === targetAgent &&
                    c.source_port === sourcePort && c.target_port === targetPort
                );

                if (existingConnection) {
                    console.warn("Connection already exists.");
                } else {
                     createConnectionOnServer(sourceAgent, targetAgent, sourcePort, targetPort);
                }
            }
            resetConnectionDrawingState();
        }
    }

    function onDrawingConnectionMouseMove(e) {
        if (!isDrawingConnection || !tempLine) return;
        const canvasRect = canvas.getBoundingClientRect();
        const x2 = e.clientX - canvasRect.left + canvas.scrollLeft;
        const y2 = e.clientY - canvasRect.top + canvas.scrollTop;
        tempLine.setAttribute('x2', x2);
        tempLine.setAttribute('y2', y2);
    }

    async function createConnectionOnServer(sourceAgentId, targetAgentId, sourcePortName, targetPortName) {
        const newConnectionData = {
            source_agent_id: sourceAgentId,
            target_agent_id: targetAgentId,
            source_port: sourcePortName, // In future, could be more specific like 'output_value'
            target_port: targetPortName,   // e.g., 'input_prompt'
        };
        try {
            const createdConnection = await apiPost('connections', newConnectionData);
            connections[createdConnection.id] = createdConnection;
            renderConnections();
        } catch (error) {
            console.error("Error creating connection:", error);
            flowOutputContent.textContent = `Error creating connection: ${error.message}`;
        }
    }

    function resetConnectionDrawingState() {
        isDrawingConnection = false;
        connectionStartAgentId = null;
        connectionStartPortType = null;
        if (tempLine) {
            tempLine.style.display = 'none'; // Hide it, or remove and recreate
        }
        document.removeEventListener('mousemove', onDrawingConnectionMouseMove);
        // Re-render connections to ensure temp line is gone if it was part of main SVG
        renderConnections();
    }


    // "Run Flow" button
    runFlowButton.addEventListener('click', async () => {
        flowOutputContent.textContent = "Running flow...";
        try {
            // The backend /api/flow/run uses its own current state of agents and connections
            const result = await apiPost('flow/run', {}); // Empty body, server uses its current state

            let outputText = `Run Result:\n${result.message}\n\n`;
            outputText += `Execution Order:\n${result.execution_order?.join(' -> ') || 'N/A'}\n\n`;
            outputText += `Simulation Details:\n`;
            if (result.simulation_details && Array.isArray(result.simulation_details)) {
                result.simulation_details.forEach(detail => {
                    outputText += `${detail}\n`;
                });
            } else {
                 outputText += JSON.stringify(result.simulation_details, null, 2) + '\n';
            }

            flowOutputContent.textContent = outputText;
        } catch (error) {
            console.error("Error running flow:", error);
            flowOutputContent.textContent = `Error running flow: ${error.message}`;
        }
    });

    // Initial call to render an empty canvas or existing elements if any (though loadInitialData handles this)
    renderAll();
});
