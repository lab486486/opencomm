export const categories = [
  {
    slug: 'drama',
    name: '드라마',
    tone: 'red',
    description: '지상파부터 tvN, JTBC까지 최신 드라마 실시간 시청 안내',
    wpSlugs: ['drama', '드라마'],
  },
  {
    slug: 'entertainment',
    name: '예능',
    tone: 'orange',
    description: '관찰 예능, 토크쇼, 오디션의 실시간·다시보기 정보',
    wpSlugs: ['entertainment', '예능-다시보기', '예능'],
  },
  {
    slug: 'sport',
    name: '스포츠',
    tone: 'green',
    description: '축구, 야구, 올림픽 등 공식 중계 일정과 시청 방법',
    wpSlugs: ['sport', '스포츠'],
  },
  {
    slug: 'movie',
    name: '영화',
    tone: 'purple',
    description: '영화 채널과 OTT의 방영·특선 정보',
    wpSlugs: ['movie', '영화'],
  },
  {
    slug: 'channel',
    name: '실시간 채널',
    tone: 'blue',
    description: 'KBS, MBC, SBS, 종편, 케이블 공식 온에어 안내',
    wpSlugs: ['channel', '실시간'],
  },
  {
    slug: 'archive',
    name: '아카이브',
    tone: 'gray',
    description: '이전 안내 글과 보관 자료',
    wpSlugs: ['etc', 'archive', 'uncategorized', '미분류'],
  },
] as const;

export type CategorySlug = (typeof categories)[number]['slug'];

export function getCategory(slug: string) {
  return categories.find((category) => category.slug === slug);
}

export function categoryPath(slug: string) {
  return `/category/${slug}/`;
}
