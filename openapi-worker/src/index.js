import openapiSchema from './openapi.json';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Only allow GET requests to /openapi.json
    if (request.method !== 'GET' || url.pathname !== '/openapi.json') {
      return new Response('Not Found', { status: 404 });
    }

    // Check for Authorization header
    const authHeader = request.headers.get('Authorization');
    const expectedToken = `Bearer ${env.API_KEY}`;

    if (!authHeader || authHeader !== expectedToken) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
          'WWW-Authenticate': 'Bearer'
        }
      });
    }

    // Serve the OpenAPI schema
    return new Response(JSON.stringify(openapiSchema), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=3600'
      }
    });
  },
};
