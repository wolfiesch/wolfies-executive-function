/**
 * Axios HTTP client configuration
 *
 * Provides a configured axios instance for all API calls with:
 * - Base URL configuration (proxied through Vite to localhost:8000)
 * - Request/response interceptors for error handling
 * - Type-safe response handling
 */

import axios, { AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'
import type { ApiResponse } from '@/types/models'

// API configuration
const API_CONFIG = {
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
}

/**
 * Custom error class for API errors
 * Provides structured error information from API responses
 */
export class ApiError extends Error {
  public readonly status: number
  public readonly code?: string
  public readonly details?: Record<string, unknown>

  constructor(
    message: string,
    status: number,
    code?: string,
    details?: Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /**
   * Check if error is a specific HTTP status
   */
  isStatus(status: number): boolean {
    return this.status === status
  }

  /**
   * Check if error is a client error (4xx)
   */
  isClientError(): boolean {
    return this.status >= 400 && this.status < 500
  }

  /**
   * Check if error is a server error (5xx)
   */
  isServerError(): boolean {
    return this.status >= 500
  }
}

/**
 * Create and configure the axios instance
 */
function createApiClient(): AxiosInstance {
  const client = axios.create(API_CONFIG)

  // Request interceptor
  client.interceptors.request.use(
    (config) => {
      // Add any auth tokens here when authentication is implemented
      // const token = getAuthToken()
      // if (token) {
      //   config.headers.Authorization = `Bearer ${token}`
      // }
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      return response
    },
    (error: AxiosError<{ error?: string; message?: string; details?: Record<string, unknown> }>) => {
      // Handle network errors
      if (!error.response) {
        throw new ApiError(
          'Network error. Please check your connection.',
          0,
          'NETWORK_ERROR'
        )
      }

      const { status, data } = error.response
      const message = data?.error || data?.message || getDefaultErrorMessage(status)

      throw new ApiError(message, status, undefined, data?.details)
    }
  )

  return client
}

/**
 * Get default error message based on HTTP status code
 */
function getDefaultErrorMessage(status: number): string {
  switch (status) {
    case 400:
      return 'Invalid request. Please check your input.'
    case 401:
      return 'Authentication required. Please log in.'
    case 403:
      return 'You do not have permission to perform this action.'
    case 404:
      return 'The requested resource was not found.'
    case 409:
      return 'This action conflicts with existing data.'
    case 422:
      return 'Validation failed. Please check your input.'
    case 429:
      return 'Too many requests. Please try again later.'
    case 500:
      return 'Server error. Please try again later.'
    case 502:
      return 'Service temporarily unavailable.'
    case 503:
      return 'Service temporarily unavailable. Please try again later.'
    default:
      return 'An unexpected error occurred.'
  }
}

// Create the singleton client instance
export const apiClient = createApiClient()

/**
 * Type-safe API request helpers
 * These wrap axios methods with proper typing for our API response format.
 *
 * Handles both:
 * - Direct responses (FastAPI style): { tasks: [...] }
 * - Wrapped responses (legacy): { data: { tasks: [...] } }
 */
export const api = {
  /**
   * Extract data from response, handling both wrapped and direct formats
   */
  extractData<T>(data: T | ApiResponse<T>): T {
    // Check if it's a wrapped response with a 'data' property
    if (data && typeof data === 'object' && 'data' in data && !('tasks' in data) && !('events' in data) && !('notes' in data) && !('goals' in data)) {
      return (data as ApiResponse<T>).data
    }
    return data as T
  },

  /**
   * GET request
   */
  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await apiClient.get<T | ApiResponse<T>>(url, { params })
    return this.extractData(response.data)
  },

  /**
   * POST request
   */
  async post<T>(url: string, data?: unknown): Promise<T> {
    const response = await apiClient.post<T | ApiResponse<T>>(url, data)
    return this.extractData(response.data)
  },

  /**
   * PUT request
   */
  async put<T>(url: string, data?: unknown): Promise<T> {
    const response = await apiClient.put<T | ApiResponse<T>>(url, data)
    return this.extractData(response.data)
  },

  /**
   * PATCH request
   */
  async patch<T>(url: string, data?: unknown): Promise<T> {
    const response = await apiClient.patch<T | ApiResponse<T>>(url, data)
    return this.extractData(response.data)
  },

  /**
   * DELETE request
   */
  async delete<T = void>(url: string): Promise<T> {
    const response = await apiClient.delete<T | ApiResponse<T>>(url)
    return this.extractData(response.data)
  },
}

export default apiClient
