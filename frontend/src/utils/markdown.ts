import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: false,            // 支持换行符转换为 <br>
  gfm: true,                // 启用 GitHub 风格的 Markdown
})

/**
 * 处理 HTML 中的链接，使其在新标签页打开
 * @param html HTML 字符串
 * @returns 处理后的 HTML
 */
function processLinks(html: string): string {
  return html.replaceAll(/<a\s+([^>]*?)>/gi, (match, attrs) => {
    // 检查是否已经有 target="_blank"
    if (/\s+target\s*=/i.test(attrs)) {
      // 如果已经有 target，检查是否为 "_blank"
      if (/\s+target\s*=\s*["_']?_blank["_']?/i.test(attrs)) {
        return match
      }
      // 如果有其他 target 值，不修改
      return match
    }
    // 添加 target="_blank" 和 rel="noopener noreferrer"
    return `<a ${attrs} target="_blank" rel="noopener noreferrer">`
  })
}

/**
 * 将 Markdown 文本转换为 HTML
 * @param markdown Markdown 文本
 * @returns HTML 字符串
 */
export function parseMarkdown(markdown: string): string {
  if (!markdown) return ''
  
  try {
    const html = marked.parse(markdown) as string
    return processLinks(html)
  } catch (error) {
    console.error('Markdown 解析失败:', error)
    return markdown
  }
}
