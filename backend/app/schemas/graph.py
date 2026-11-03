from pydantic import BaseModel, Field


class EntityNode(BaseModel):
    id: str
    label: str
    type: str


class RelationEdge(BaseModel):
    source: str
    target: str
    type: str
    confidence: float


class GraphOut(BaseModel):
    paper_id: int
    title: str
    exists: bool = False
    nodes: list[EntityNode] = Field(default_factory=list)
    edges: list[RelationEdge] = Field(default_factory=list)


class AnnotateResult(BaseModel):
    paper_id: int
    entities: int
    relations: int


class BatchAnnotateResult(BaseModel):
    project_id: int
    total: int = 0
    annotated: int = 0
    entities: int = 0
    relations: int = 0
    errors: list[str] = Field(default_factory=list)


class GraphStats(BaseModel):
    nodes: int
    relations: int
    papers: int
