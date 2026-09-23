import sys
import logging
from typing import Literal
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context

# Ensure logs go exclusively to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("customer-mcp-server")

mcp = FastMCP("CustomerServiceMCP", port=8001)

# In-memory customer dataset
CUSTOMERS_DB = {
    "cust_101": {
        "id": "cust_101",
        "name": "Sarah Connor",
        "tier": "enterprise",
        "clearance": "level_4",
        "status": "active"
    },
    "cust_102": {
        "id": "cust_102",
        "name": "Miles Dyson",
        "tier": "standard",
        "clearance": "level_1",
        "status": "suspended"
    }
}

class CustomerQuery(BaseModel):
    customer_id: str = Field(..., description="Customer ID, e.g. cust_101 or cust_102")

@mcp.tool()
async def get_customer_details(query: CustomerQuery, ctx: Context) -> dict:
    """Fetch customer profile, account tier, clearance level, and status."""
    logger.info(f"Tool executed: fetching customer {query.customer_id}")
    cust = CUSTOMERS_DB.get(query.customer_id)
    if not cust:
        return {"error": f"Customer '{query.customer_id}' not found."}
    return cust

if __name__ == "__main__":
    logger.info("Starting MCP Server on SSE transport at port 8001...")
    mcp.run(transport="sse")    