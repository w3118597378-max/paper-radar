// Cloudflare Pages Function: /api/arxiv
// 转发 arXiv API 请求并加 CORS 头（arXiv 官方 API 无 CORS，浏览器无法直连）
// 无任何密钥，仅转发公开论文数据
const ARXIV_API = 'https://export.arxiv.org/api/query';

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const target = new URL(ARXIV_API);
  target.search = url.search;

  const resp = await fetch(target.toString(), {
    headers: { 'User-Agent': 'paper-radar-demo/0.1' },
  });

  const headers = new Headers(resp.headers);
  headers.set('Access-Control-Allow-Origin', '*');
  headers.set('Access-Control-Allow-Methods', 'GET, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Content-Type');

  return new Response(resp.body, { status: resp.status, headers });
}
