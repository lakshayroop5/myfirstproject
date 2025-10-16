"""
Database tools for various database systems.

This module provides tools for interacting with different database systems
including PostgreSQL, Neo4j, MongoDB, and others.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
import logging

from .base import Tool, ToolResult, ToolStatus, ToolError

logger = logging.getLogger(__name__)


class BaseDatabaseTool(Tool):
    """Base class for database tools."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.connection = None
        
    async def connect(self):
        """Establish database connection."""
        pass
    
    async def disconnect(self):
        """Close database connection."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class PostgreSQLTool(BaseDatabaseTool):
    """Tool for PostgreSQL database operations."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.url = config.get('url')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config.get('database')
        self.username = config.get('username')
        self.password = config.get('password')
        self.pool_size = config.get('pool_size', 10)
        self.pool = None
        
    def validate_config(self) -> bool:
        """Validate PostgreSQL configuration."""
        if self.url:
            return True
        if not all([self.host, self.database, self.username, self.password]):
            logger.error(f"Missing required PostgreSQL configuration for {self.name}")
            return False
        return True
    
    async def connect(self):
        """Establish PostgreSQL connection pool."""
        try:
            import asyncpg
        except ImportError:
            raise ToolError("asyncpg library not installed. Run: pip install asyncpg", self.name)
        
        try:
            if self.url:
                self.pool = await asyncpg.create_pool(
                    self.url,
                    min_size=1,
                    max_size=self.pool_size
                )
            else:
                self.pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    min_size=1,
                    max_size=self.pool_size
                )
            logger.info(f"Connected to PostgreSQL: {self.name}")
        except Exception as e:
            raise ToolError(f"Failed to connect to PostgreSQL: {e}", self.name, e)
    
    async def disconnect(self):
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info(f"Disconnected from PostgreSQL: {self.name}")
    
    async def execute(self, query: str, params: List = None, fetch: str = "all", **kwargs) -> ToolResult:
        """
        Execute PostgreSQL query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Fetch mode ('all', 'one', 'none')
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with query results
        """
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as conn:
                if fetch == "none":
                    # Execute without fetching (INSERT, UPDATE, DELETE)
                    result = await conn.execute(query, *(params or []))
                    data = {"affected_rows": result, "query": query}
                elif fetch == "one":
                    # Fetch single row
                    result = await conn.fetchrow(query, *(params or []))
                    data = {"result": dict(result) if result else None, "query": query}
                else:
                    # Fetch all rows (default)
                    result = await conn.fetch(query, *(params or []))
                    data = {"result": [dict(row) for row in result], "query": query, "row_count": len(result)}
                
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    data=data
                )
                
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"PostgreSQL query error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get PostgreSQL tool schema."""
        return {
            "name": self.name,
            "description": "PostgreSQL database tool for executing SQL queries",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute",
                    "required": True
                },
                "params": {
                    "type": "array",
                    "description": "Query parameters",
                    "required": False
                },
                "fetch": {
                    "type": "string",
                    "description": "Fetch mode: 'all', 'one', or 'none'",
                    "default": "all",
                    "enum": ["all", "one", "none"]
                }
            },
            "required": ["query"],
            "examples": [
                {
                    "query": "SELECT * FROM users WHERE age > $1",
                    "params": [25],
                    "fetch": "all"
                },
                {
                    "query": "INSERT INTO users (name, email) VALUES ($1, $2)",
                    "params": ["John Doe", "john@example.com"],
                    "fetch": "none"
                }
            ]
        }


class Neo4jTool(BaseDatabaseTool):
    """Tool for Neo4j graph database operations."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.uri = config.get('uri')
        self.username = config.get('username')
        self.password = config.get('password')
        self.database = config.get('database', 'neo4j')
        self.driver = None
        
    def validate_config(self) -> bool:
        """Validate Neo4j configuration."""
        if not all([self.uri, self.username, self.password]):
            logger.error(f"Missing required Neo4j configuration for {self.name}")
            return False
        return True
    
    async def connect(self):
        """Establish Neo4j connection."""
        try:
            from neo4j import AsyncGraphDatabase
        except ImportError:
            raise ToolError("neo4j library not installed. Run: pip install neo4j", self.name)
        
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            await self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j: {self.name}")
        except Exception as e:
            raise ToolError(f"Failed to connect to Neo4j: {e}", self.name, e)
    
    async def disconnect(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info(f"Disconnected from Neo4j: {self.name}")
    
    async def execute(self, query: str, params: Dict = None, **kwargs) -> ToolResult:
        """
        Execute Neo4j Cypher query.
        
        Args:
            query: Cypher query to execute
            params: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with query results
        """
        if not self.driver:
            await self.connect()
        
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, params or {})
                records = await result.data()
                
                data = {
                    "result": records,
                    "query": query,
                    "record_count": len(records)
                }
                
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    data=data
                )
                
        except Exception as e:
            logger.error(f"Neo4j query error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"Neo4j query error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get Neo4j tool schema."""
        return {
            "name": self.name,
            "description": "Neo4j graph database tool for executing Cypher queries",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "Cypher query to execute",
                    "required": True
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters",
                    "required": False
                }
            },
            "required": ["query"],
            "examples": [
                {
                    "query": "MATCH (n:Person) WHERE n.age > $age RETURN n",
                    "params": {"age": 25}
                },
                {
                    "query": "CREATE (n:Person {name: $name, email: $email}) RETURN n",
                    "params": {"name": "John Doe", "email": "john@example.com"}
                }
            ]
        }


class MongoDBTool(BaseDatabaseTool):
    """Tool for MongoDB operations."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.uri = config.get('uri')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 27017)
        self.database = config.get('database')
        self.username = config.get('username')
        self.password = config.get('password')
        self.client = None
        self.db = None
        
    def validate_config(self) -> bool:
        """Validate MongoDB configuration."""
        if self.uri:
            return True
        if not self.database:
            logger.error(f"Database name required for MongoDB tool {self.name}")
            return False
        return True
    
    async def connect(self):
        """Establish MongoDB connection."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError:
            raise ToolError("motor library not installed. Run: pip install motor", self.name)
        
        try:
            if self.uri:
                self.client = AsyncIOMotorClient(self.uri)
            else:
                connection_string = f"mongodb://"
                if self.username and self.password:
                    connection_string += f"{self.username}:{self.password}@"
                connection_string += f"{self.host}:{self.port}"
                self.client = AsyncIOMotorClient(connection_string)
            
            self.db = self.client[self.database]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.name}")
        except Exception as e:
            raise ToolError(f"Failed to connect to MongoDB: {e}", self.name, e)
    
    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info(f"Disconnected from MongoDB: {self.name}")
    
    async def execute(self, operation: str, collection: str, 
                     query: Dict = None, document: Dict = None,
                     documents: List[Dict] = None, **kwargs) -> ToolResult:
        """
        Execute MongoDB operation.
        
        Args:
            operation: Operation type ('find', 'insert_one', 'insert_many', 'update_one', etc.)
            collection: Collection name
            query: Query filter
            document: Document for single operations
            documents: Documents for bulk operations
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with operation results
        """
        if not self.db:
            await self.connect()
        
        try:
            coll = self.db[collection]
            
            if operation == "find":
                cursor = coll.find(query or {})
                result = await cursor.to_list(length=kwargs.get('limit', 100))
                data = {"result": result, "count": len(result)}
                
            elif operation == "find_one":
                result = await coll.find_one(query or {})
                data = {"result": result}
                
            elif operation == "insert_one":
                result = await coll.insert_one(document)
                data = {"inserted_id": str(result.inserted_id)}
                
            elif operation == "insert_many":
                result = await coll.insert_many(documents)
                data = {"inserted_ids": [str(id) for id in result.inserted_ids]}
                
            elif operation == "update_one":
                result = await coll.update_one(query, document)
                data = {"matched_count": result.matched_count, "modified_count": result.modified_count}
                
            elif operation == "update_many":
                result = await coll.update_many(query, document)
                data = {"matched_count": result.matched_count, "modified_count": result.modified_count}
                
            elif operation == "delete_one":
                result = await coll.delete_one(query)
                data = {"deleted_count": result.deleted_count}
                
            elif operation == "delete_many":
                result = await coll.delete_many(query)
                data = {"deleted_count": result.deleted_count}
                
            else:
                raise ToolError(f"Unknown operation: {operation}", self.name)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=data
            )
            
        except Exception as e:
            logger.error(f"MongoDB operation error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"MongoDB operation error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get MongoDB tool schema."""
        return {
            "name": self.name,
            "description": "MongoDB database tool for document operations",
            "parameters": {
                "operation": {
                    "type": "string",
                    "description": "Operation type",
                    "required": True,
                    "enum": ["find", "find_one", "insert_one", "insert_many", 
                            "update_one", "update_many", "delete_one", "delete_many"]
                },
                "collection": {
                    "type": "string",
                    "description": "Collection name",
                    "required": True
                },
                "query": {
                    "type": "object",
                    "description": "Query filter",
                    "required": False
                },
                "document": {
                    "type": "object",
                    "description": "Document for operations",
                    "required": False
                },
                "documents": {
                    "type": "array",
                    "description": "Documents for bulk operations",
                    "required": False
                }
            },
            "required": ["operation", "collection"],
            "examples": [
                {
                    "operation": "find",
                    "collection": "users",
                    "query": {"age": {"$gt": 25}}
                },
                {
                    "operation": "insert_one",
                    "collection": "users",
                    "document": {"name": "John Doe", "email": "john@example.com"}
                }
            ]
        }