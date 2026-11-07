export const GRAPH_TYPES = {
  CONCEPT: { label: '概念', color: '#2f6bff' },
  METHOD: { label: '方法', color: '#0f8a9e' },
  DATASET: { label: '数据集', color: '#6557d8' },
  ACRONYM: { label: '缩写', color: '#c17a1f' },
  PERSON: { label: '人物', color: '#c2557a' },
  ORG: { label: '机构', color: '#0e9f6e' },
}

export function graphType(type) {
  return GRAPH_TYPES[type] || GRAPH_TYPES.CONCEPT
}
