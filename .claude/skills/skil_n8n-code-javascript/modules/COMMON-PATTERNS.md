# Common Patterns - JavaScript Code Node

10 production-tested patterns for n8n Code nodes.

---

## Pattern 1: Multi-Source Data Aggregation

Combine data from multiple APIs/webhooks into unified structure.

```javascript
const allItems = $input.all();
let articles = [];

for (const item of allItems) {
  const name = item.json.name || 'Unknown';
  const data = item.json;

  if (name === 'Hacker News' && data.hits) {
    for (const hit of data.hits) {
      articles.push({
        title: hit.title, url: hit.url,
        summary: hit.story_text || 'No summary',
        source: 'Hacker News', score: hit.points || 0,
        fetchedAt: new Date().toISOString()
      });
    }
  } else if (name === 'Reddit' && data.data?.children) {
    for (const post of data.data.children) {
      articles.push({
        title: post.data.title, url: post.data.url,
        summary: post.data.selftext || 'No summary',
        source: 'Reddit', score: post.data.score || 0,
        fetchedAt: new Date().toISOString()
      });
    }
  }
}

articles.sort((a, b) => b.score - a.score);
return articles.map(a => ({json: a}));
```

**Variations:** Add source weighting (`score * weights[source]`), filter by min score, deduplicate by URL with `Set`.

---

## Pattern 2: Regex Filtering & Extraction

Extract mentions, keywords, emails, phones from text.

```javascript
const pattern = /\b([A-Z]{2,5})\b/g;
const knownTerms = ['VOO', 'VTI', 'SPY', 'QQQ'];
const mentions = {};

for (const item of $input.all()) {
  const data = item.json.data;
  if (!data?.children) continue;

  for (const post of data.children) {
    const text = ((post.data.title || '') + ' ' + (post.data.selftext || '')).toUpperCase();
    const matches = text.match(pattern);
    if (!matches) continue;

    for (const match of matches) {
      if (!knownTerms.includes(match)) continue;
      if (!mentions[match]) mentions[match] = { count: 0, totalScore: 0, posts: [] };
      mentions[match].count++;
      mentions[match].totalScore += post.data.score || 0;
      mentions[match].posts.push({ title: post.data.title, score: post.data.score });
    }
  }
}

return Object.entries(mentions)
  .map(([term, data]) => ({ json: { term, mentions: data.count, avgScore: data.totalScore / data.count } }))
  .sort((a, b) => b.json.mentions - a.json.mentions);
```

**Other regex patterns:** Email: `/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g`, Phone: `/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g`, Hashtags: `/#(\w+)/g`, URLs: `/https?:\/\/[^\s]+/g`

---

## Pattern 3: Markdown Parsing

Parse structured text into JSON using regex groups.

```javascript
const markdown = $input.first().json.data.markdown;
const adRegex = /##\s*(.*?)\n(.*?)(?=\n##|\n---|$)/gs;
const ads = [];
let match;

function parseTimeToMinutes(str) {
  if (!str) return 999999;
  const d = str.match(/(\d+)\s*day/), h = str.match(/(\d+)\s*hour/), m = str.match(/(\d+)\s*min/);
  return (d ? parseInt(d[1]) * 1440 : 0) + (h ? parseInt(h[1]) * 60 : 0) + (m ? parseInt(m[1]) : 0);
}

while ((match = adRegex.exec(markdown)) !== null) {
  const title = match[1]?.trim() || 'No title';
  const content = match[2]?.trim() || '';
  const district = content.match(/\*\*District:\*\*\s*(.*?)(?:\n|$)/)?.[1]?.trim() || 'Unknown';
  const time = content.match(/Posted:\s*(.*?)\*/)?.[1];

  ads.push({ title, district, timeInMinutes: parseTimeToMinutes(time), fullContent: content });
}

ads.sort((a, b) => a.timeInMinutes - b.timeInMinutes);
return ads.map(ad => ({json: ad}));
```

**Variations:** HTML table parsing, code block extraction, YAML frontmatter parsing.

---

## Pattern 4: JSON Comparison

Detect changes between two versions of data.

```javascript
const orderKeys = (obj) => { const o = {}; Object.keys(obj).sort().forEach(k => o[k] = obj[k]); return o; };
const allItems = $input.all();
const original = orderKeys(JSON.parse(Buffer.from(allItems[0].json.content, 'base64').toString()));
const current = orderKeys(allItems[1].json);

const diffs = [];
for (const key of Object.keys(original)) {
  if (JSON.stringify(original[key]) !== JSON.stringify(current[key]))
    diffs.push({ field: key, original: original[key], current: current[key] });
}
for (const key of Object.keys(current)) {
  if (!(key in original)) diffs.push({ field: key, original: null, current: current[key], status: 'new' });
}

return [{ json: { identical: diffs.length === 0, differenceCount: diffs.length, differences: diffs } }];
```

**Variations:** Simple equality (`JSON.stringify(a) === JSON.stringify(b)`), recursive deep diff, schema validation.

---

## Pattern 5: CRM Data Transformation

Normalize form/contact data into CRM-compatible format.

```javascript
const { name, email, phone, company, course_interest, message, timestamp } = $input.all()[0].json;
const [firstName, ...rest] = name.split(' ');
const lastName = rest.join(' ') || 'Unknown';

return [{ json: {
  crmData: {
    data: {
      type: 'Contact',
      attributes: {
        first_name: firstName, last_name: lastName,
        email1: email, phone_work: phone.replace(/[^\d]/g, ''),
        account_name: company, lead_source: 'Website Form', status: 'New',
        description: `Interest: ${course_interest}\nMessage: ${message}`
      }
    }
  },
  processed: true
}}];
```

**Variations:** Batch processing with `.map()`, field validation/normalization, lead scoring.

---

## Pattern 6: Release Processing

Filter and extract version info from GitHub API responses.

```javascript
const releases = $input.first().json
  .filter(r => !r.prerelease && !r.draft)
  .slice(0, 10)
  .map(r => ({
    tag: r.tag_name, name: r.name, published: r.published_at,
    author: r.author.login, url: r.html_url,
    highlights: r.body?.includes('## Highlights:')
      ? r.body.split('## Highlights:')[1]?.split('##')[0]?.trim()
      : (r.body || '').substring(0, 500),
    assets: r.assets.map(a => ({ name: a.name, size: a.size, downloads: a.download_count }))
  }));

return releases.map(r => ({json: r}));
```

---

## Pattern 7: Array Transformation with Context

Add computed fields, rankings, age calculations.

```javascript
const releases = $input.first().json
  .filter(r => !r.prerelease && !r.draft)
  .slice(0, 10)
  .map(r => ({
    version: r.tag_name,
    assetCount: r.assets.length,
    isRecent: new Date(r.published_at) > new Date(Date.now() - 30 * 86400000),
    age: Math.floor((Date.now() - new Date(r.published_at)) / 86400000) + ' days ago'
  }));

return releases.map(r => ({json: r}));
```

**Variations:** Add ranking with `.map((item, i) => ({...item, rank: i+1}))`), percentage calculations, category labels.

---

## Pattern 8: Slack Block Kit Formatting

Build rich Slack messages with structured blocks.

```javascript
const date = new Date().toISOString().split('T')[0];
const data = $input.first().json;

return [{ json: {
  text: `Daily Report - ${date}`,
  blocks: [
    { type: "header", text: { type: "plain_text", text: `Daily Report - ${date}` } },
    { type: "section", text: { type: "mrkdwn",
        text: `*Status:* ${data.status === 'ok' ? 'All Clear' : 'Issues'}\n*Alerts:* ${data.alertCount || 0}` } },
    { type: "divider" },
    { type: "section", fields: [
      { type: "mrkdwn", text: `*Failed Logins:*\n${data.failedLogins || 0}` },
      { type: "mrkdwn", text: `*Uptime:*\n${data.uptime || '100%'}` }
    ]}
  ]
}}];
```

**Variations:** Interactive buttons (`accessory.type: "button"`), numbered lists, status emoji mapping, truncation for 3000-char limit.

---

## Pattern 9: Top N Filtering & Ranking

Get best results by score, similarity, or composite criteria.

```javascript
const chunks = $input.item.json.chunks || [];
const topChunks = chunks
  .sort((a, b) => (b.similarity || 0) - (a.similarity || 0))
  .slice(0, 6);

return [{ json: {
  topChunks, count: topChunks.length,
  maxSimilarity: topChunks[0]?.similarity || 0,
  avgSimilarity: topChunks.reduce((s, c) => s + (c.similarity || 0), 0) / topChunks.length
}}];
```

**Variations:** Min threshold filter, bottom N (ascending sort), composite score (`relevance * 0.6 + recency * 0.4`), percentile filtering.

---

## Pattern 10: String Aggregation & Reporting

Combine text items into formatted reports.

```javascript
const allItems = $input.all();
const messages = allItems.map(item => item.json.message);
const header = `**Daily Summary**\n${new Date().toLocaleString()}\nTotal: ${messages.length}\n\n`;
const report = header + messages.join('\n\n---\n\n');

return [{ json: { report, messageCount: messages.length, generatedAt: new Date().toISOString() } }];
```

**Variations:** Numbered list (`.map((item, i) => \`${i+1}. ${item}\``), markdown table, HTML report, JSON summary with stats (total, avg, max, min).

---

## Pattern Selection

| Goal | Pattern |
|------|---------|
| Combine API responses | 1 (Aggregation) |
| Extract keywords/mentions | 2 (Regex) |
| Parse formatted text | 3 (Markdown) |
| Detect data changes | 4 (Comparison) |
| Prepare CRM data | 5 (Transformation) |
| Process releases | 6 (Release) |
| Add computed fields | 7 (Array Transform) |
| Rich Slack messages | 8 (Block Kit) |
| Top results by score | 9 (Top N) |
| Generate text reports | 10 (Aggregation) |

**Key techniques:** `map/filter/reduce/sort/slice`, regex, optional chaining (`?.`), template literals, destructuring.

---

## See Also

- [DATA_ACCESS.md](DATA_ACCESS.md) — Data access methods
- [ERROR_PATTERNS.md](ERROR_PATTERNS.md) — Common mistakes
- [BUILTIN_FUNCTIONS.md](BUILTIN_FUNCTIONS.md) — Built-in helpers
