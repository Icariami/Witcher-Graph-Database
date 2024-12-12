from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

from pydantic import BaseModel
from typing import Dict

from fastapi.middleware.cors import CORSMiddleware
# Initialize FastAPI
app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chmury-front.azurewebsites.net/"],  # Allows all origins (for testing)
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","DELETE"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Pydantic model for the add_node request
class NodeData(BaseModel):
    label: str  # Node label (e.g., Character, Ability, etc.)
    properties: Dict[str, str]  # Dynamic properties of the node

class RelationshipData(BaseModel):
    node1_label: str  # Label of the first node (e.g., "Character", "Monster")
    node1_properties: Dict[str, str]  # Properties to identify the first node
    node2_label: str  # Label of the second node (e.g., "Character", "Ability")
    node2_properties: Dict[str, str]  # Properties to identify the second node
    relationship_type: str  # Type of relationship (e.g., "FRIEND", "WEAK_TO")

URI = "neo4j+s://9a8e1e42.databases.neo4j.io"
AUTH = ("neo4j", "eErpx-x1P6HPMRzBq1Cl_zNeV6jICuJTvqSXZxLXCDI")
frontend_url = "https://chmury-front.azurewebsites.net"
with GraphDatabase.driver(URI) as driver:
    driver.verify_connectivity()
    console.log("Connection to the database established.")
    
# Root endpoint to test server
@app.get("/")
async def root():
    return {"message": "Welcome to the Witcher Database API"}


# Add a node
@app.post("/add_node")
async def add_node(data: NodeData):
    try:
        with driver.session() as session:
            query = f"CREATE (n:{data.label} $props) RETURN n"
            result = session.run(query, props=data.properties)
            node = result.single()
            return {"message": "Node added", "node": node["n"] if node else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Fetch all nodes of a label
@app.get("/get_nodes/{label}")
async def get_nodes(label: str):
    try:
        with driver.session() as session:
            query = f"MATCH (n:{label}) RETURN n"
            results = session.run(query)
            nodes = [record["n"] for record in results]
            return {"nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/add_relationship")
async def add_relationship(data: RelationshipData):
    try:
        with driver.session() as session:
            # Build dynamic property match strings
            node1_props = " AND ".join([f"a.{k} = ${k}1" for k in data.node1_properties.keys()])
            node2_props = " AND ".join([f"b.{k} = ${k}2" for k in data.node2_properties.keys()])

            query = f"""
                MATCH (a:{data.node1_label}), (b:{data.node2_label})
                WHERE {node1_props} AND {node2_props}
                CREATE (a)-[r:{data.relationship_type}]->(b)
                RETURN type(r) AS relationship
            """

            # Combine properties with unique suffixes to avoid conflicts
            parameters = {
                **{f"{k}1": v for k, v in data.node1_properties.items()},
                **{f"{k}2": v for k, v in data.node2_properties.items()},
            }

            # Execute query
            result = session.run(query, parameters)
            relationship = result.single()

            if relationship:
                return {"message": "Relationship created", "relationship": relationship["relationship"]}
            else:
                raise HTTPException(status_code=404, detail="One or both nodes not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_relationships")
async def search_relationships(data: dict):
    node1_label = data.get("node1_label")
    node1_name = data.get("node1_name")
    node2_label = data.get("node2_label")
    node2_name = data.get("node2_name")
    
    if not all([node1_label, node1_name, node2_label, node2_name]):
        raise HTTPException(status_code=400, detail="All node details are required.")
    
    try:
        with driver.session() as session:
            query = f"""
                MATCH (a:{node1_label} {{name: $node1_name}})-[r]->(b:{node2_label} {{name: $node2_name}})
                RETURN type(r) AS relationship
            """
            results = session.run(query, node1_name=node1_name, node2_name=node2_name)
            relationships = [record["relationship"] for record in results]
            if relationships:
                return {"relationships": relationships}
            else:
                return {"relationships": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_outgoing_relationships")
async def get_outgoing_relationships(data: dict):
    node_label = data.get("node_label")
    node_name = data.get("node_name")

    if not node_label or not node_name:
        raise HTTPException(status_code=400, detail="Both node label and name are required.")

    try:
        with driver.session() as session:
            query = f"""
                MATCH (n:{node_label} {{name: $node_name}})-[r]->(connected_node)
                RETURN type(r) AS relationship, properties(connected_node) AS connected_node_properties
            """
            results = session.run(query, node_name=node_name)
            relationships = [
                {"relationship": record["relationship"], "connected_node": record["connected_node_properties"]}
                for record in results
            ]
            return {"relationships": relationships}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_node_relationships")
async def get_node_relationships(data: dict):
    node_label = data.get("node_label")
    node_name = data.get("node_name")

    if not node_label or not node_name:
        raise HTTPException(status_code=400, detail="Both node label and name are required.")

    try:
        with driver.session() as session:
            query = f"""
                MATCH (n:{node_label} {{name: $node_name}})-[r]-(connected_node)
                RETURN type(r) AS relationship, properties(connected_node) AS connected_node_properties
            """
            results = session.run(query, node_name=node_name)
            relationships = [
                {"relationship": record["relationship"], "connected_node": record["connected_node_properties"]}
                for record in results
            ]
            return {"relationships": relationships}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_node_names/{label}")
async def get_node_names(label: str):
    try:
        with driver.session() as session:
            query = f"MATCH (n:{label}) RETURN n.name AS name"
            results = session.run(query)
            names = [record["name"] for record in results if record["name"] is not None]
            return {"names": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Close Neo4j driver when the app shuts down
@app.on_event("shutdown")
def shutdown():
    driver.close()

