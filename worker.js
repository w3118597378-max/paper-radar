// Paper Radar Worker: 静态资源托管 + /api/arxiv 代理
// 部署: wrangler deploy (Cloudflare Workers)
// 无任何密钥, 仅转发公开 arXiv 数据并加 CORS 头

const ARXIV_API = 'https://export.arxiv.org/api/query';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // arXiv 代理: /api/arxiv?search_query=...&max_results=...
    if (url.pathname.startsWith('/api/arxiv')) {
      const target = new URL(ARXIV_API);
      target.search = url.search;
      try {
        const resp = await fetch(target.toString(), {
          headers: { 'User-Agent': 'paper-radar-demo/0.1' },
        });
        const headers = new Headers(resp.headers);
        headers.set('Access-Control-Allow-Origin', '*');
        headers.set('Access-Control-Allow-Methods', 'GET, OPTIONS');
        headers.set('Access-Control-Allow-Headers', 'Content-Type');
        return new Response(resp.body, { status: resp.status, headers });
      } catch (e) {
        return new Response('arXiv 代理失败: ' + e.message, { status: 502 });
      }
    }

    // 其他 /api/* 请求
    if (url.pathname.startsWith('/api/')) {
      return new Response('Not Found', { status: 404 });
    }

    // 静态资源交给 Assets 托管
    return env.ASSETS.fetch(request);
  },
};
