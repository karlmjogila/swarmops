/**
 * Simple router implementation for HTTP API
 * Works with Node.js http module or can be adapted for Express
 */

import { IncomingMessage, ServerResponse } from 'http';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'OPTIONS';

export interface RouteParams {
  [key: string]: string;
}

export interface RequestContext {
  req: IncomingMessage;
  res: ServerResponse;
  params: RouteParams;
  query: URLSearchParams;
  body: unknown;
}

export type RouteHandler = (ctx: RequestContext) => Promise<void>;

interface Route {
  method: HttpMethod;
  pattern: RegExp;
  paramNames: string[];
  handler: RouteHandler;
}

/**
 * Simple router for API endpoints
 */
export class Router {
  private routes: Route[] = [];
  private basePath: string;

  constructor(basePath: string = '') {
    this.basePath = basePath.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Register a route
   */
  private register(method: HttpMethod, path: string, handler: RouteHandler): void {
    const fullPath = this.basePath + path;
    const paramNames: string[] = [];
    
    // Convert path parameters to regex
    // e.g., /roles/:id -> /roles/([^/]+)
    const patternStr = fullPath.replace(/:([^/]+)/g, (_, name) => {
      paramNames.push(name);
      return '([^/]+)';
    });

    this.routes.push({
      method,
      pattern: new RegExp(`^${patternStr}$`),
      paramNames,
      handler,
    });
  }

  get(path: string, handler: RouteHandler): this {
    this.register('GET', path, handler);
    return this;
  }

  post(path: string, handler: RouteHandler): this {
    this.register('POST', path, handler);
    return this;
  }

  put(path: string, handler: RouteHandler): this {
    this.register('PUT', path, handler);
    return this;
  }

  patch(path: string, handler: RouteHandler): this {
    this.register('PATCH', path, handler);
    return this;
  }

  delete(path: string, handler: RouteHandler): this {
    this.register('DELETE', path, handler);
    return this;
  }

  /**
   * Mount another router at a path prefix
   */
  use(path: string, router: Router): this {
    for (const route of router.routes) {
      const fullPath = path + route.pattern.source.slice(1, -1); // Remove ^ and $
      this.routes.push({
        ...route,
        pattern: new RegExp(`^${fullPath}$`),
      });
    }
    return this;
  }

  /**
   * Handle an incoming request
   */
  async handle(req: IncomingMessage, res: ServerResponse): Promise<boolean> {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    const method = req.method?.toUpperCase() as HttpMethod;
    const pathname = url.pathname;

    for (const route of this.routes) {
      if (route.method !== method) continue;

      const match = pathname.match(route.pattern);
      if (!match) continue;

      // Extract params
      const params: RouteParams = {};
      route.paramNames.forEach((name, i) => {
        params[name] = decodeURIComponent(match[i + 1]);
      });

      // Parse body for POST/PUT/PATCH
      let body: unknown = null;
      if (['POST', 'PUT', 'PATCH'].includes(method)) {
        body = await parseJsonBody(req);
      }

      const ctx: RequestContext = {
        req,
        res,
        params,
        query: url.searchParams,
        body,
      };

      await route.handler(ctx);
      return true;
    }

    return false;
  }

  /**
   * Get all registered routes (for debugging)
   */
  getRoutes(): { method: HttpMethod; pattern: string }[] {
    return this.routes.map(r => ({
      method: r.method,
      pattern: r.pattern.source,
    }));
  }
}

/**
 * Parse JSON body from request
 */
async function parseJsonBody(req: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', chunk => data += chunk);
    req.on('end', () => {
      if (!data) {
        resolve(null);
        return;
      }
      try {
        resolve(JSON.parse(data));
      } catch {
        reject(new Error('Invalid JSON body'));
      }
    });
    req.on('error', reject);
  });
}

/**
 * Send JSON response
 */
export function json(res: ServerResponse, data: unknown, status: number = 200): void {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  });
  res.end(JSON.stringify(data));
}

/**
 * Send error response
 */
export function error(res: ServerResponse, message: string, status: number = 500): void {
  json(res, { error: message }, status);
}

/**
 * Send 404 Not Found
 */
export function notFound(res: ServerResponse, message: string = 'Not found'): void {
  error(res, message, 404);
}

/**
 * Send 400 Bad Request
 */
export function badRequest(res: ServerResponse, message: string): void {
  error(res, message, 400);
}

/**
 * Send 409 Conflict
 */
export function conflict(res: ServerResponse, message: string): void {
  error(res, message, 409);
}
