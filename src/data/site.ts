export const site = {
  name: '온에어 Live',
  tagline: '실시간 드라마 · 예능 · 스포츠 방송 안내',
  description: '공중파 3사와 종편, tvN, ENA까지 공식 온에어 주소와 편성 정보를 모아 안내합니다.',
  url: 'https://opencomm.net',
  imageBase: import.meta.env.PUBLIC_IMAGE_BASE ?? '',
};

export const popularQueries = [
  { label: 'SBS 실시간', query: 'SBS 실시간' },
  { label: 'ENA 실시간', query: 'ENA 실시간' },
  { label: 'tvN 실시간', query: 'tvN 실시간' },
];

export const channels = [
  { name: 'KBS 1TV', href: '/kbs1-실시간-온에어/', tone: 'kbs' },
  { name: 'KBS 2TV', href: '/kbs2-실시간-온에어-편성표/', tone: 'kbs' },
  { name: 'MBC', href: '/mbc-실시간-온에어/', tone: 'mbc' },
  { name: 'SBS', href: '/sbs-실시간-온에어/', tone: 'sbs' },
  { name: 'JTBC', href: '/jtbc-실시간-온에어/', tone: 'jtbc' },
  { name: 'TV조선', href: '/티비조선-실시간-온에어-다시보기/', tone: 'chosun' },
  { name: '채널A', href: '/채널에이-실시간-온에어-채널a/', tone: 'channela' },
  { name: 'MBN', href: '/mbn-실시간-온에어-다시보기/', tone: 'mbn' },
  { name: 'tvN', href: '/티비엔-실시간-tvn-온에어/', tone: 'tvn' },
  { name: 'ENA', href: '/ena-실시간-온에어/', tone: 'ena' },
  { name: '연합뉴스TV', href: 'https://www.yonhapnewstv.co.kr/live/', tone: 'news', external: true },
  { name: 'YTN', href: 'https://www.ytn.co.kr/live/', tone: 'news', external: true },
  { name: '쿠팡플레이', href: 'https://www.coupangplay.com/', tone: 'ott', external: true },
  { name: '티빙', href: 'https://www.tving.com/', tone: 'ott', external: true },
  { name: '스포티비 나우', href: 'https://www.spotvnow.co.kr/', tone: 'sport', external: true },
  { name: 'Mnet', href: 'https://www.mnetplus.world/', tone: 'mnet', external: true },
];

export const scheduleLinks = [
  {
    group: 'SBS / KBS / MBC',
    label: '공중파 편성표',
    href: 'https://search.naver.com/search.naver?query=%EA%B3%B5%EC%A4%91%ED%8C%8C+%ED%8E%B8%EC%84%B1%ED%91%9C',
  },
  {
    group: 'tvN / ENA / Mnet',
    label: '케이블 편성표',
    href: 'https://search.naver.com/search.naver?query=%EC%BC%80%EC%9D%B4%EB%B8%94+%ED%8E%B8%EC%84%B1%ED%91%9C',
  },
  {
    group: '채널A / MBN / JTBC / TV조선',
    label: '종편 편성표',
    href: 'https://search.naver.com/search.naver?query=%EC%A2%85%ED%8E%B8+%ED%8E%B8%EC%84%B1%ED%91%9C',
  },
  {
    group: '스카이라이프',
    label: '위성 편성표',
    href: 'https://search.naver.com/search.naver?query=%EC%8A%A4%EC%B9%B4%EC%9D%B4%EB%9D%BC%EC%9D%B4%ED%94%84+%ED%8E%B8%EC%84%B1%ED%91%9C',
  },
];

export const athleteQueries = [
  { label: '김혜성', sub: 'LA 다저스', query: '김혜성' },
  { label: '손흥민', sub: 'LA 갤럭시', query: '손흥민' },
  { label: '김민재', sub: 'FC 바이에른 뮌헨', query: '김민재' },
  { label: '조규성', sub: 'FC 미트윌란', query: '조규성' },
];

export const entertainmentRecaps = [
  { name: '무한도전', href: 'https://onair.imbc.com/MbicPlay?channelid=50' },
  { name: '나혼자산다', href: 'https://onair.imbc.com/MbicPlay?channelid=49' },
  { name: '런닝맨', href: 'https://www.sbs.co.kr/live/S22?div=live_list' },
  { name: '1박2일', href: 'https://program.kbs.co.kr/2tv/enter/1n2d/pc/index.html' },
  { name: '전원일기', href: 'https://onair.imbc.com/MbicPlay?channelid=43' },
  { name: '대한외국인', href: 'https://onair.imbc.com/MbicPlay?channelid=95' },
  { name: '웬만해선 그들을...', href: 'https://www.sbs.co.kr/live/S32?div=live_list' },
  { name: '슈퍼맨이 돌아왔다', href: 'https://program.kbs.co.kr/2tv/enter/superman/pc/index.html' },
];

export const faqs = [
  {
    q: '실시간 방송은 무료인가요?',
    a: '각 방송사에서 공식적으로 제공하는 온에어 서비스는 대부분 무료로 시청할 수 있습니다. 일부 서비스는 로그인이 필요할 수 있습니다.',
  },
  {
    q: '불법 스트리밍 사이트인가요?',
    a: '아닙니다. 공중파·종편·스포츠 채널의 공식 홈페이지 온에어 주소만 링크 형식으로 안내하는 정보 큐레이션 사이트입니다. 영상을 직접 올리지 않습니다.',
  },
  {
    q: '별도의 앱을 다운로드해야 하나요?',
    a: '컴퓨터는 웹브라우저로 바로 접속할 수 있습니다. 스마트폰에서는 각 방송사 공식 앱으로 연결될 수 있습니다.',
  },
  {
    q: '해외에서도 시청이 가능한가요?',
    a: '방송사 정책에 따라 해외 IP는 차단될 수 있습니다. 이 경우 해당 국가의 라이선스를 가진 서비스를 이용해야 합니다.',
  },
];
