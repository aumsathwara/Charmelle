import sys
import math
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import SessionLocal

app = FastAPI()

class RecommendationRequest(BaseModel):
    conditions: List[str]
    budget_max: Optional[float] = None
    budget_min: Optional[float] = None
    sort: str = "rating"
    limit: int = 10

class ProductRecommendation(BaseModel):
    product_id: str
    brand: str
    name: str
    min_price: Optional[float]
    avg_rating: Optional[float]
    offer_count: int

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/recommend", response_model=List[ProductRecommendation])
def recommend_products(request: RecommendationRequest):
    """
    Get product recommendations based on skin conditions and budget.
    """
    session = SessionLocal()
    try:
        # Build the base query
        query_parts = []
        params = {}
        
        # Base query with condition filtering
        base_query = """
        SELECT DISTINCT p.product_id, p.brand, p.name, p.min_price, p.avg_rating, p.offer_count
        FROM products_latest p
        JOIN condition_tags ct ON p.product_id = ct.product_id
        WHERE ct.condition = ANY(:conditions)
        """
        query_parts.append(base_query)
        params['conditions'] = request.conditions
        
        # Add budget filters
        if request.budget_min is not None:
            query_parts.append("AND p.min_price >= :budget_min")
            params['budget_min'] = request.budget_min
            
        if request.budget_max is not None:
            query_parts.append("AND p.min_price <= :budget_max")
            params['budget_max'] = request.budget_max
        
        # Add price filter to exclude products without prices
        query_parts.append("AND p.min_price IS NOT NULL")
        
        # Add sorting
        if request.sort == "rating":
            query_parts.append("ORDER BY p.avg_rating DESC NULLS LAST, p.min_price ASC")
        elif request.sort == "price_low":
            query_parts.append("ORDER BY p.min_price ASC, p.avg_rating DESC NULLS LAST")
        elif request.sort == "price_high":
            query_parts.append("ORDER BY p.min_price DESC, p.avg_rating DESC NULLS LAST")
        elif request.sort == "brand":
            query_parts.append("ORDER BY p.brand ASC, p.avg_rating DESC NULLS LAST")
        else:
            query_parts.append("ORDER BY p.avg_rating DESC NULLS LAST, p.min_price ASC")
        
        # Add limit
        query_parts.append("LIMIT :limit")
        params['limit'] = request.limit
        
        # Execute query
        full_query = " ".join(query_parts)
        result = session.execute(text(full_query), params).fetchall()
        
        # Format results
        recommendations = []
        for row in result:
            # Handle NaN values in avg_rating
            avg_rating = row[4]
            if avg_rating is not None:
                avg_rating = float(avg_rating)
                if math.isnan(avg_rating):  # Check for NaN
                    avg_rating = None
            
            recommendations.append(ProductRecommendation(
                product_id=row[0],
                brand=row[1] or "",
                name=row[2] or "",
                min_price=float(row[3]) if row[3] is not None else None,
                avg_rating=avg_rating,
                offer_count=int(row[5]) if row[5] is not None else 0
            ))
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 