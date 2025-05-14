// MCP 서비스 타입 정의
export interface McpService {
  id: string
  name: string
  icon: string
  active: boolean
  is_selected: boolean
  required_env_vars: { key: string; value: string }[]
}

// API 응답 타입 정의
export interface McpServiceResponse {
  public_id: string
  name: string
  mcp_type: string
  description: string
  required_env_vars: string[]
  is_selected: boolean
} 