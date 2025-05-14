import api from './api';
import { McpServiceResponse } from '../types/mcp';
// import axios from 'axios';

// MCP 서비스 목록 조회 API
export const fetchMcpServices = async (): Promise<McpServiceResponse[]> => {
  try {
    const response = await api.get('/api/mcps/');
    // const response = await axios.get('https://k12b107.p.ssafy.io/api/mcps');
    return response.data as McpServiceResponse[];
  } catch (error) {
    console.error('MCP 서비스 API 호출 실패:', error);
    return []; // 에러 발생 시 빈 배열 반환
  }
};

// 환경변수 조회 API
export const fetchEnvironmentVariables = async (): Promise<Record<string, Record<string, string>>> => {
  try {
    const response = await api.get('/api/env/');
    // const response = await axios.get('https://k12b107.p.ssafy.io/api/env');
    console.log('환경변수 조회 성공:', response.data);
    return response.data as Record<string, Record<string, string>>; // 타입 단언
  } catch (error) {
    console.error('환경변수 조회 실패:', error);
    return {}; // 에러 발생 시 빈 객체 반환
  }
};

// 특정 MCP 서비스의 환경변수만 조회하는 API
export const fetchEnvironmentVariablesByService = async (public_id: string): Promise<Record<string, string>> => {
  try {
    console.log(`서비스 ID: ${public_id}로 환경변수 조회 요청`);
    const response = await api.get(`/api/env/${public_id}`);
    // const response = await axios.get(`https://k12b107.p.ssafy.io/api/env/${public_id}`);
    console.log(`${public_id} 서비스 환경변수 조회 응답:`, response);
    console.log(`${public_id} 서비스 환경변수 조회 데이터:`, response.data);
    
    // API 응답이 다양한 형태로 올 수 있으므로 구조를 확인하고 적절히 처리
    let envVars: Record<string, string> = {};
    
    if (response.data) {
      const data = response.data as Record<string, any>;
      
      // env_settings 객체가 존재하는 경우 (예: {public_id: '...', env_settings: {NOTION_API_TOKEN: '...'}})
      if (data.env_settings && typeof data.env_settings === 'object') {
        console.log('env_settings 객체 발견:', data.env_settings);
        Object.entries(data.env_settings).forEach(([key, value]) => {
          if (typeof value === 'string') {
            envVars[key] = value;
          } else if (value !== null && value !== undefined) {
            envVars[key] = String(value);
          }
        });
      } 
      // 응답이 직접 환경변수 객체인 경우 (예: {NOTION_API_TOKEN: '...'})
      else if (typeof data === 'object' && !Array.isArray(data)) {
        // public_id와 환경변수가 아닌 필드 제외
        const { public_id: pid, ...rest } = data;
        
        // 나머지 필드를 환경변수로 처리
        Object.entries(rest).forEach(([key, value]) => {
          if (key !== 'env_settings' && typeof value === 'string') {
            envVars[key] = value;
          } else if (key !== 'env_settings' && value !== null && value !== undefined) {
            envVars[key] = String(value);
          }
        });
      } else if (Array.isArray(response.data)) {
        // 응답이 배열인 경우 (예: [{key: "key1", value: "value1"}, ...])
        response.data.forEach((item: any) => {
          if (item.key && (item.value !== undefined && item.value !== null)) {
            envVars[item.key] = String(item.value);
          }
        });
      }
    }
    
    console.log(`${public_id} 서비스 환경변수 변환 결과:`, envVars);
    return envVars;
  } catch (error) {
    console.error(`${public_id} 서비스 환경변수 조회 실패:`, error);
    return {}; // 에러 발생 시 빈 객체 반환
  }
};

// MCP 서비스 설정 저장 API
export const saveMcpServiceSettings = async (services: any[]): Promise<void> => {
  try {
    // 활성화 상태와 관계없이 전달된 서비스 사용 (active 상태 체크 제거)
    if (services.length === 0) {
      console.warn('저장할 서비스가 없습니다.');
      return;
    }
    
    // API 문서 형식에 맞게 데이터 변환
    const payload: { 
      public_id: string; 
      env_vars: Record<string, string>; 
    } = {
      public_id: services[0].id, // McpService의 id는 서버의 public_id와 동일
      env_vars: {}
    };
    
    // 환경변수 객체로 변환 - 모든 값을 명시적으로 포함시킴(빈 문자열 포함)
    services[0].required_env_vars.forEach((env: { key: string; value: string }) => {
      // 값이 undefined인 경우만 빈 문자열로 변환, 나머지는 그대로 전송 (빈 문자열도 그대로 유지)
      payload.env_vars[env.key] = env.value === undefined ? "" : env.value;
    });
    
    // 단일 객체로 POST 요청
    console.log('저장할 환경변수 데이터:', payload);
    await api.post('/api/env/', payload);
    // await axios.post('https://k12b107.p.ssafy.io/api/env', payload);
  } catch (error) {
    console.error('MCP 서비스 환경변수 설정 저장 실패:', error);
    throw error; // 에러를 상위로 전파
  }
};

// MCP 서비스 선택 토글 API - 선택 또는 선택 취소를 자동으로 처리
export const toggleMcpSelection = async (public_id: string, isCurrentlySelected: boolean): Promise<boolean> => {
  try {
    let response;
    
    if (isCurrentlySelected) {
      // 이미 선택된 상태라면 선택 취소
      response = await api.delete(`/api/select/${public_id}`);
      // response = await axios.delete(`https://k12b107.p.ssafy.io/api/select/${public_id}`);
      console.log('MCP 선택 취소 성공:', response.data);
    } else {
      // 선택되지 않은 상태라면 선택
      response = await api.post(`/api/select/${public_id}`);
      // response = await axios.post(`https://k12b107.p.ssafy.io/api/select/${public_id}`);
      console.log('MCP 선택 성공:', response.data);
    }
    
    return !isCurrentlySelected; // 토글된 상태 반환
  } catch (error) {
    console.error('MCP 선택 상태 변경 실패:', error);
    throw error;
  }
};

// POD 생성 API - 설정된 MCP 서비스로 POD 생성
export const createPod = async (): Promise<any> => {
  try {
    const response = await api.post('/api/pod');
    // const response = await axios.post('https://k12b107.p.ssafy.io/api/pod');
    console.log('POD 생성 성공:', response.data);
    return response.data;
  } catch (error) {
    console.error('POD 생성 실패:', error);
    throw error;
  }
};