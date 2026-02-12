"""
Semantic search functionality using pgvector and embeddings.
Enables finding similar strategy rules based on their descriptions and conditions.
"""

import hashlib
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..database.models import StrategyRuleDB
from .models import StrategyRule
from .cache import cache_manager, CacheKeys, CacheTTL


class EmbeddingGenerator:
    """Generate embeddings for text using available LLM APIs."""
    
    def __init__(self):
        self.anthropic_api_key = settings.anthropic_api_key
        self.openai_api_key = settings.openai_api_key
        self._embedding_dim = 1536  # OpenAI embedding dimension
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        # For now, use a simple implementation
        # In production, use OpenAI's text-embedding-3-small or similar
        
        if self.openai_api_key:
            return self._generate_openai_embedding(text)
        else:
            # Fallback to simple hash-based embedding for development
            return self._generate_simple_embedding(text)
    
    def _generate_openai_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI embedding error: {e}")
            return self._generate_simple_embedding(text)
    
    def _generate_simple_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """
        Generate simple hash-based embedding for development/testing.
        Not suitable for production but allows testing without API keys.
        """
        # Create deterministic hash
        text_hash = hashlib.sha256(text.encode()).digest()
        
        # Convert hash to numbers and normalize
        numbers = np.frombuffer(text_hash, dtype=np.uint8).astype(float)
        
        # Expand to desired dimension by repeating and adding noise
        embedding = np.tile(numbers, (dim // len(numbers)) + 1)[:dim]
        
        # Normalize to unit vector
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.tolist()
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._embedding_dim


class SemanticSearch:
    """Semantic search for strategy rules using vector similarity."""
    
    def __init__(self, session: Session):
        """
        Initialize semantic search.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.embedding_generator = EmbeddingGenerator()
        self._ensure_pgvector_extension()
    
    def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is installed and enabled."""
        try:
            # Try to create the extension (will fail silently if already exists)
            self.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.session.commit()
        except Exception as e:
            print(f"Could not create pgvector extension: {e}")
            # Not critical for basic functionality
    
    def _add_embedding_column_if_needed(self):
        """Add embedding column to strategy_rules table if it doesn't exist."""
        try:
            # Check if column exists
            result = self.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='strategy_rules' AND column_name='embedding'
            """))
            
            if not result.fetchone():
                # Add embedding column
                dim = self.embedding_generator.embedding_dimension
                self.session.execute(text(f"""
                    ALTER TABLE strategy_rules 
                    ADD COLUMN embedding vector({dim})
                """))
                
                # Create index for similarity search
                self.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_strategy_embedding 
                    ON strategy_rules 
                    USING ivfflat (embedding vector_cosine_ops)
                """))
                
                self.session.commit()
                print("Added embedding column to strategy_rules table")
        except Exception as e:
            self.session.rollback()
            print(f"Error adding embedding column: {e}")
    
    def generate_rule_embedding_text(self, rule: StrategyRuleDB) -> str:
        """
        Generate text representation of a strategy rule for embedding.
        
        Args:
            rule: Strategy rule database model
            
        Returns:
            Text representation combining name, description, and key attributes
        """
        parts = [
            f"Strategy: {rule.name}",
            f"Entry Type: {rule.entry_type}",
        ]
        
        if rule.description:
            parts.append(f"Description: {rule.description}")
        
        # Add conditions summary
        if rule.conditions:
            conditions_text = ", ".join(
                f"{c.get('type', 'unknown')} on {c.get('timeframe', 'unknown')}"
                for c in rule.conditions
            )
            parts.append(f"Conditions: {conditions_text}")
        
        # Add tags
        if rule.tags:
            parts.append(f"Tags: {', '.join(rule.tags)}")
        
        return " | ".join(parts)
    
    def update_rule_embedding(self, rule_id: str) -> bool:
        """
        Update embedding for a specific strategy rule.
        
        Args:
            rule_id: Strategy rule ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the rule
            rule = self.session.query(StrategyRuleDB).filter_by(id=rule_id).first()
            if not rule:
                return False
            
            # Generate text representation
            rule_text = self.generate_rule_embedding_text(rule)
            
            # Generate embedding
            embedding = self.embedding_generator.generate_embedding(rule_text)
            if not embedding:
                return False
            
            # Update rule with embedding
            # Note: This requires the embedding column to exist
            try:
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                self.session.execute(
                    text(f"UPDATE strategy_rules SET embedding = :embedding WHERE id = :id"),
                    {"embedding": embedding_str, "id": rule_id}
                )
                self.session.commit()
                return True
            except Exception as e:
                print(f"Error updating embedding (pgvector might not be available): {e}")
                self.session.rollback()
                return False
                
        except Exception as e:
            print(f"Error updating rule embedding: {e}")
            self.session.rollback()
            return False
    
    def find_similar_rules(
        self,
        rule_id: str,
        limit: int = 10,
        min_confidence: Optional[float] = None
    ) -> List[Tuple[StrategyRule, float]]:
        """
        Find similar strategy rules using vector similarity.
        
        Args:
            rule_id: Strategy rule ID to find similar rules for
            limit: Maximum number of similar rules to return
            min_confidence: Minimum confidence score filter
            
        Returns:
            List of tuples (StrategyRule, similarity_score)
        """
        # Check cache first
        cache_key = CacheKeys.similar_rules(rule_id, limit)
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            # Convert cached dicts back to StrategyRule objects
            return [
                (self._dict_to_strategy_rule(rule_dict), score)
                for rule_dict, score in cached_result
            ]
        
        try:
            # Get the reference rule
            ref_rule = self.session.query(StrategyRuleDB).filter_by(id=rule_id).first()
            if not ref_rule:
                return []
            
            # Try vector similarity search
            similar_rules = self._vector_similarity_search(rule_id, limit, min_confidence)
            
            if not similar_rules:
                # Fallback to tag-based similarity
                similar_rules = self._tag_based_similarity(ref_rule, limit, min_confidence)
            
            # Cache the results (convert to serializable format)
            cache_data = [
                (self._strategy_rule_to_dict(rule), score)
                for rule, score in similar_rules
            ]
            cache_manager.set(cache_key, cache_data, CacheTTL.SIMILAR_RULES)
            
            return similar_rules
            
        except Exception as e:
            print(f"Error finding similar rules: {e}")
            return []
    
    def _vector_similarity_search(
        self,
        rule_id: str,
        limit: int,
        min_confidence: Optional[float]
    ) -> List[Tuple[StrategyRule, float]]:
        """Perform vector similarity search using pgvector."""
        try:
            # Build query with cosine similarity
            query = text("""
                SELECT 
                    sr.*,
                    1 - (sr.embedding <=> ref.embedding) as similarity
                FROM strategy_rules sr
                CROSS JOIN strategy_rules ref
                WHERE ref.id = :rule_id
                AND sr.id != :rule_id
                AND sr.embedding IS NOT NULL
            """)
            
            if min_confidence:
                query = text(str(query) + " AND sr.confidence >= :min_confidence")
            
            query = text(str(query) + """
                ORDER BY sr.embedding <=> ref.embedding
                LIMIT :limit
            """)
            
            params = {"rule_id": rule_id, "limit": limit}
            if min_confidence:
                params["min_confidence"] = min_confidence
            
            result = self.session.execute(query, params)
            
            similar_rules = []
            for row in result:
                # Convert row to StrategyRule
                rule = self._row_to_strategy_rule(row)
                similarity = row.similarity
                similar_rules.append((rule, similarity))
            
            return similar_rules
            
        except Exception as e:
            print(f"Vector similarity search failed: {e}")
            return []
    
    def _tag_based_similarity(
        self,
        ref_rule: StrategyRuleDB,
        limit: int,
        min_confidence: Optional[float]
    ) -> List[Tuple[StrategyRule, float]]:
        """Fallback similarity search based on tags and entry type."""
        query = self.session.query(StrategyRuleDB).filter(
            StrategyRuleDB.id != ref_rule.id
        )
        
        if min_confidence:
            query = query.filter(StrategyRuleDB.confidence >= min_confidence)
        
        # Prioritize same entry type
        query = query.order_by(
            (StrategyRuleDB.entry_type == ref_rule.entry_type).desc(),
            StrategyRuleDB.confidence.desc()
        )
        
        similar_rules = []
        for db_rule in query.limit(limit * 2):  # Get more for filtering
            # Calculate similarity score based on attributes
            score = 0.0
            
            # Same entry type
            if db_rule.entry_type == ref_rule.entry_type:
                score += 0.3
            
            # Overlapping tags
            if ref_rule.tags and db_rule.tags:
                common_tags = set(ref_rule.tags) & set(db_rule.tags)
                tag_similarity = len(common_tags) / max(len(ref_rule.tags), len(db_rule.tags))
                score += 0.4 * tag_similarity
            
            # Similar confidence level
            if ref_rule.confidence and db_rule.confidence:
                conf_diff = abs(ref_rule.confidence - db_rule.confidence)
                score += 0.3 * (1 - conf_diff)
            
            if score > 0:
                rule = self._db_to_strategy_rule(db_rule)
                similar_rules.append((rule, score))
        
        # Sort by score and limit
        similar_rules.sort(key=lambda x: x[1], reverse=True)
        return similar_rules[:limit]
    
    def _db_to_strategy_rule(self, db_rule: StrategyRuleDB) -> StrategyRule:
        """Convert database model to Pydantic model."""
        from .models import ContentSource, RiskParameters
        
        return StrategyRule(
            id=db_rule.id,
            name=db_rule.name,
            source=ContentSource(
                type=db_rule.source_type,
                ref=db_rule.source_ref,
                timestamp=db_rule.source_timestamp,
                page_number=db_rule.source_page_number
            ),
            entry_type=db_rule.entry_type,
            conditions=db_rule.conditions or [],
            confluence_required=db_rule.confluence_required or [],
            risk_params=RiskParameters(**db_rule.risk_params) if db_rule.risk_params else RiskParameters(),
            confidence=db_rule.confidence,
            created_at=db_rule.created_at,
            last_used=db_rule.last_used,
            trade_count=db_rule.trade_count,
            win_rate=db_rule.win_rate,
            avg_r_multiple=db_rule.avg_r_multiple,
            description=db_rule.description,
            tags=db_rule.tags or []
        )
    
    def _row_to_strategy_rule(self, row) -> StrategyRule:
        """Convert query row to StrategyRule."""
        from .models import ContentSource, RiskParameters
        
        return StrategyRule(
            id=row.id,
            name=row.name,
            source=ContentSource(
                type=row.source_type,
                ref=row.source_ref,
                timestamp=row.source_timestamp,
                page_number=row.source_page_number
            ),
            entry_type=row.entry_type,
            conditions=row.conditions or [],
            confluence_required=row.confluence_required or [],
            risk_params=RiskParameters(**row.risk_params) if row.risk_params else RiskParameters(),
            confidence=row.confidence,
            created_at=row.created_at,
            last_used=row.last_used,
            trade_count=row.trade_count,
            win_rate=row.win_rate,
            avg_r_multiple=row.avg_r_multiple,
            description=row.description,
            tags=row.tags or []
        )
    
    def _strategy_rule_to_dict(self, rule: StrategyRule) -> Dict[str, Any]:
        """Convert StrategyRule to dict for caching."""
        return rule.dict()
    
    def _dict_to_strategy_rule(self, rule_dict: Dict[str, Any]) -> StrategyRule:
        """Convert dict to StrategyRule."""
        return StrategyRule(**rule_dict)


__all__ = [
    "EmbeddingGenerator",
    "SemanticSearch",
]
