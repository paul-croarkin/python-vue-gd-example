<script setup>
import { computed, nextTick, onMounted, ref } from 'vue';

const filters = ref({ song: '', venue: '', date: '', min_rating: '0', sort_by: 'newest' });
const results = ref([]);
const total = ref(0);
const page = ref(1);
const pages = ref(0);
const selectedShow = ref(null);
const showDetails = ref(null);
const activeTrack = ref(null);
const audioPlayer = ref(null);
const isPlaying = ref(false);
const isWholeShowPlaying = ref(false);
const loading = ref(false);
const detailLoading = ref(false);
const error = ref('');
const detailError = ref('');

const resultRange = computed(() => {
  if (!total.value) return 'No recordings found';
  const label = results.value.length === 1 ? 'unique show' : 'unique shows';
  return `${results.value.length} ${label} · ${total.value.toLocaleString()} archive recordings`;
});

async function searchShows(nextPage = 1) {
  loading.value = true;
  error.value = '';
  page.value = nextPage;

  const params = new URLSearchParams({ page: String(nextPage) });
  if (filters.value.song.trim()) params.set('song', filters.value.song.trim());
  if (filters.value.venue.trim()) params.set('venue', filters.value.venue.trim());
  if (filters.value.date) params.set('date', filters.value.date);
  if (Number(filters.value.min_rating)) params.set('min_rating', filters.value.min_rating);
  params.set('sort_by', filters.value.sort_by);

  try {
    const response = await fetch(`/api/search?${params}`);
    if (!response.ok) throw new Error(await responseMessage(response));
    const payload = await response.json();
    results.value = payload.results;
    total.value = payload.total;
    pages.value = payload.pages;
    const current = results.value.find((show) => show.identifier === selectedShow.value?.identifier);
    await selectShow(current || results.value[0] || null);
  } catch (cause) {
    error.value = cause.message || 'The archive search could not be completed.';
    results.value = [];
    total.value = 0;
    pages.value = 0;
    await selectShow(null);
  } finally {
    loading.value = false;
  }
}

async function responseMessage(response) {
  try {
    const payload = await response.json();
    return payload.detail || 'The archive request failed.';
  } catch {
    return 'The archive request failed.';
  }
}

async function selectShow(show) {
  selectedShow.value = show;
  showDetails.value = null;
  activeTrack.value = null;
  isPlaying.value = false;
  isWholeShowPlaying.value = false;
  detailError.value = '';
  if (!show) return;

  detailLoading.value = true;
  try {
    const response = await fetch(`/api/item/${encodeURIComponent(show.identifier)}`);
    if (!response.ok) throw new Error(await responseMessage(response));
    showDetails.value = await response.json();
    activeTrack.value = showDetails.value.tracks[0] || null;
  } catch (cause) {
    detailError.value = cause.message || 'Show details could not be loaded.';
  } finally {
    detailLoading.value = false;
  }
}

function clearFilters() {
  filters.value = { song: '', venue: '', date: '', min_rating: '0', sort_by: 'newest' };
  searchShows();
}

function formatDate(value) {
  if (!value) return 'Date unknown';
  const parsed = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parsed);
}

function trackLabel(name) {
  const match = name.match(/-d(\d+)t(\d+)/i);
  return match ? `Disc ${match[1]} · Track ${match[2]}` : name;
}

async function playTrack(track, continueWholeShow = false) {
  isWholeShowPlaying.value = continueWholeShow;
  if (activeTrack.value?.url === track.url && isPlaying.value) {
    audioPlayer.value?.pause();
    return;
  }
  activeTrack.value = track;
  await nextTick();
  const player = audioPlayer.value;
  if (!player) return;
  try {
    await player.play();
    if (audioPlayer.value === player) isPlaying.value = !player.paused;
  } catch {
    if (audioPlayer.value === player) isPlaying.value = false;
  }
}

async function toggleWholeShowPlayback() {
  if (isWholeShowPlaying.value && isPlaying.value) {
    audioPlayer.value?.pause();
    return;
  }

  const track = isWholeShowPlaying.value
    ? activeTrack.value
    : showDetails.value?.tracks[0];
  if (track) await playTrack(track, true);
}

function handlePlayerPlay(event) {
  if (event.currentTarget === audioPlayer.value) isPlaying.value = true;
}

function handlePlayerPause(event) {
  if (event.currentTarget === audioPlayer.value) {
    isPlaying.value = !event.currentTarget.paused;
  }
}

function playNextTrack() {
  const tracks = showDetails.value?.tracks || [];
  const currentIndex = tracks.findIndex((track) => track.url === activeTrack.value?.url);
  const nextTrack = tracks[currentIndex + 1];
  if (nextTrack) {
    playTrack(nextTrack, isWholeShowPlaying.value);
  } else {
    isPlaying.value = false;
    isWholeShowPlaying.value = false;
  }
}

function formatRating(value) {
  const rating = Number(value);
  return Number.isFinite(rating) && rating > 0 ? rating.toFixed(2) : 'Unrated';
}

onMounted(() => searchShows());
</script>

<template>
  <div class="app-shell">
    <header class="masthead">
      <a class="wordmark" href="#top" aria-label="Dead Archive home">
        <span class="wordmark-mark" aria-hidden="true">GD</span>
        <span>DEAD<span class="wordmark-light">ARCHIVE</span></span>
      </a>
      <a class="archive-link" href="https://archive.org/details/GratefulDead" target="_blank" rel="noreferrer">
        INTERNET ARCHIVE <span aria-hidden="true">↗</span>
      </a>
    </header>

    <main id="top">
      <section class="intro" aria-labelledby="page-title">
        <div class="intro-copy">
          <p class="eyebrow"><span class="live-dot"></span> A LISTENING ROOM FOR THE PEOPLE</p>
          <h1 id="page-title">Every show<br /><em>has a story.</em></h1>
          <p class="intro-description">Explore the tapes, rooms, and nights that made the Grateful Dead live archive.</p>
        </div>
        <div class="intro-stamp" aria-hidden="true">
          <span class="stamp-small">TAPES FROM</span>
          <span class="stamp-large">’65—’95</span>
          <span class="stamp-small">AND EVERYTHING BETWEEN</span>
        </div>
      </section>

      <section class="search-panel" aria-label="Search recordings">
        <form class="search-form" @submit.prevent="searchShows(1)">
          <label class="filter-field song-field">
            <span class="field-label">SONG OR SETLIST</span>
            <span class="input-wrap"><span class="search-icon" aria-hidden="true">⌕</span><input v-model="filters.song" type="search" placeholder="Try ‘Scarlet Begonias’" /></span>
          </label>
          <label class="filter-field venue-field">
            <span class="field-label">VENUE</span>
            <input v-model="filters.venue" type="search" placeholder="Try ‘Barton Hall’" />
          </label>
          <label class="filter-field date-field">
            <span class="field-label">SHOW DATE</span>
            <input v-model="filters.date" type="date" />
          </label>
          <label class="filter-field rating-field">
            <span class="field-label">MIN. FAN RATING</span>
            <select v-model="filters.min_rating">
              <option value="0">Any rating</option>
              <option value="3">3+ stars</option>
              <option value="4">4+ stars</option>
              <option value="4.5">4.5+ stars</option>
            </select>
          </label>
          <label class="filter-field sort-field">
            <span class="field-label">SORT BY</span>
            <select v-model="filters.sort_by">
              <option value="newest">Newest shows</option>
              <option value="oldest">Oldest shows</option>
              <option value="rating">Highest rated</option>
              <option value="reviews">Most reviewed</option>
            </select>
          </label>
          <button class="search-button" type="submit" :disabled="loading">
            <span aria-hidden="true">⌕</span> {{ loading ? 'Searching' : 'Find a show' }}
          </button>
        </form>
        <div class="search-footnote"><span>18,000+ recordings</span><span class="footnote-divider"></span><span>Free to explore & listen</span><button class="clear-button" type="button" @click="clearFilters">Clear filters</button></div>
      </section>

      <section class="listening-layout" aria-label="Search results and selected show">
        <div class="results-section">
          <div class="results-heading">
            <div>
              <p class="eyebrow section-eyebrow">THE TAPE SHELF</p>
            </div>
            <span class="result-count">{{ resultRange }}</span>
          </div>

          <p v-if="error" class="status-message error-message" role="alert">{{ error }}</p>
          <div v-else-if="loading && !results.length" class="status-message">Opening the archive…</div>
          <div v-else-if="!results.length" class="status-message">No tapes match those filters. Try a different song, date, or rating.</div>
          <div v-else class="show-list">
            <button
              v-for="(show, index) in results"
              :key="show.identifier"
              class="show-row"
              :class="{ selected: selectedShow?.identifier === show.identifier }"
              type="button"
              :aria-pressed="selectedShow?.identifier === show.identifier"
              @click="selectShow(show)"
            >
              <span class="row-number">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="show-art"><img :src="show.artwork" :alt="''" loading="lazy" @error="$event.target.style.visibility = 'hidden'" /><span class="art-placeholder" aria-hidden="true">GD</span></span>
              <span class="show-copy">
                <span class="show-date">{{ formatDate(show.date) }}<span v-if="show.venue" class="show-venue"> · {{ show.venue }}</span></span>
                <span class="show-title">{{ show.title }}</span>
                <span class="show-location">{{ show.coverage || 'Grateful Dead' }}<span v-if="show.recording_count > 1"> · {{ show.recording_count }} tape copies</span></span>
              </span>
              <span class="show-rating"><span class="star" aria-hidden="true">★</span> {{ formatRating(show.avg_rating) }}<small>{{ Number(show.num_reviews || 0).toLocaleString() }} reviews</small></span>
              <span class="row-arrow" aria-hidden="true">↗</span>
            </button>
          </div>

          <nav v-if="pages > 1" class="pagination" aria-label="Result pages">
            <button type="button" :disabled="page <= 1 || loading" @click="searchShows(page - 1)">← Previous</button>
            <span>PAGE {{ page }} OF {{ pages }}</span>
            <button type="button" :disabled="page >= pages || loading" @click="searchShows(page + 1)">Next →</button>
          </nav>
        </div>

        <aside class="show-panel" aria-label="Selected show details">
          <div v-if="!selectedShow" class="empty-detail">
            <span class="empty-glyph" aria-hidden="true">✳</span>
            <p>Pick a show from the shelf to open the tape.</p>
          </div>
          <template v-else>
            <div class="detail-art-wrap">
              <img class="detail-art" :src="selectedShow.artwork" :alt="`Artwork for ${selectedShow.title}`" @error="$event.target.style.visibility = 'hidden'" />
              <div class="detail-art-placeholder" aria-hidden="true"><span>GRATEFUL DEAD</span><strong>LIVE<br />TAPE</strong><span>{{ formatDate(selectedShow.date) }}</span></div>
              <span class="art-caption">FROM THE INTERNET ARCHIVE</span>
            </div>

            <div class="detail-heading">
              <p class="eyebrow section-eyebrow">NOW ON THE DECKS</p>
              <h2>{{ selectedShow.title }}</h2>
              <p class="detail-meta">{{ formatDate(selectedShow.date) }}<span v-if="selectedShow.venue"> · {{ selectedShow.venue }}</span></p>
              <p v-if="selectedShow.coverage" class="detail-location">{{ selectedShow.coverage }}</p>
              <div class="detail-rating"><span class="star" aria-hidden="true">★</span><strong>{{ formatRating(selectedShow.avg_rating) }}</strong><span>from {{ Number(selectedShow.num_reviews || 0).toLocaleString() }} listener reviews</span></div>
            </div>

            <div class="player-block">
              <div class="player-head">
                <div class="player-label"><span class="player-live-dot"></span> ARCHIVE PLAYER</div>
                <button
                  class="whole-show-button"
                  type="button"
                  :disabled="detailLoading || !showDetails?.tracks.length"
                  @click="toggleWholeShowPlayback"
                >
                  <span aria-hidden="true">{{ isWholeShowPlaying && isPlaying ? 'Ⅱ' : '▶' }}</span>
                  {{ isWholeShowPlaying ? (isPlaying ? 'Pause show' : 'Resume show') : 'Play whole show' }}
                </button>
              </div>
              <p v-if="detailLoading" class="player-status">Loading show files…</p>
              <p v-else-if="detailError" class="player-status error-message" role="alert">{{ detailError }}</p>
              <template v-else-if="showDetails?.tracks.length">
                <div class="track-list-heading"><span>SONGS</span><span>{{ showDetails.tracks.length }} TRACKS</span></div>
                <div class="track-list" aria-label="Songs in this show">
                  <button
                    v-for="track in showDetails.tracks"
                    :key="track.url"
                    class="track-row"
                    :class="{ 'track-row-active': activeTrack?.url === track.url }"
                    type="button"
                    :aria-label="`${activeTrack?.url === track.url && isPlaying ? 'Pause' : 'Play'} ${track.title || trackLabel(track.name)}`"
                    :aria-pressed="activeTrack?.url === track.url"
                    @click="playTrack(track)"
                  >
                    <span class="track-play-icon" aria-hidden="true">{{ activeTrack?.url === track.url && isPlaying ? 'Ⅱ' : '▶' }}</span>
                    <span class="track-copy">
                      <span class="track-title">{{ track.title || trackLabel(track.name) }}</span>
                      <span class="track-subtitle">{{ trackLabel(track.name) }}</span>
                    </span>
                    <span class="track-number">{{ String(track.track_number || 0).padStart(2, '0') }}</span>
                  </button>
                </div>
                <audio v-if="activeTrack" ref="audioPlayer" :key="activeTrack.url" controls preload="none" :src="activeTrack.url" @play="handlePlayerPlay" @pause="handlePlayerPause" @ended="playNextTrack">Your browser does not support audio playback.</audio>
                <a class="archive-item-link" :href="`https://archive.org/details/${selectedShow.identifier}`" target="_blank" rel="noreferrer">ALL FILES & SHOW NOTES <span aria-hidden="true">↗</span></a>
              </template>
              <p v-else-if="showDetails" class="player-status">No browser-playable audio files are available for this tape.</p>
            </div>

            <section class="description-block" aria-labelledby="description-title">
              <h3 id="description-title">SETLIST & NOTES <span aria-hidden="true">✳</span></h3>
              <p v-if="showDetails?.description">{{ showDetails.description }}</p>
              <p v-else-if="showDetails?.notes">{{ showDetails.notes }}</p>
              <p v-else class="muted-copy">No setlist or description has been added for this recording.</p>
            </section>
          </template>
        </aside>
      </section>
    </main>

    <footer class="site-footer"><span>DEAD ARCHIVE <span class="footer-dot">✳</span> BUILT ON THE TAPE TRADES</span><span>RECORDINGS HOSTED BY THE <a href="https://archive.org/details/GratefulDead" target="_blank" rel="noreferrer">INTERNET ARCHIVE ↗</a></span></footer>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {
  font-family: 'DM Sans', sans-serif;
  color: #20231f;
  background: #f4f5f1;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  --ink: #20231f;
  --muted: #777c72;
  --line: #dfe2da;
  --paper: #f4f5f1;
  --white: #fff;
  --green: #164d3b;
  --orange: #d15b37;
  --yellow: #e5b848;
  --mono: 'DM Mono', monospace;
  --serif: 'Newsreader', Georgia, serif;
}

* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; background: var(--paper); }
button, input, select { font: inherit; }
button, a, select { -webkit-tap-highlight-color: transparent; }
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid #d15b3777; outline-offset: 3px; }
a { color: inherit; }
.app-shell { max-width: 1512px; margin: 0 auto; padding: 0 6.2%; animation: arrive 480ms ease-out both; }
.masthead { height: 74px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--line); }
.wordmark { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; font: 500 14px var(--mono); letter-spacing: 0; }
.wordmark-mark { width: 30px; height: 30px; display: grid; place-items: center; background: var(--green); color: #fff; border-radius: 50%; font: 500 10px var(--mono); }
.wordmark-light { color: var(--green); }
.archive-link, .site-footer, .eyebrow, .field-label, .search-footnote, .result-count, .row-number, .show-date, .show-location, .show-rating small, .art-caption, .player-label, .track-select-label, .archive-item-link, .description-block h3, .pagination span { font: 10px var(--mono); letter-spacing: 0; }
.archive-link { color: #51574e; text-decoration: none; }
.archive-link span { color: var(--orange); padding-left: 4px; }
.intro { display: flex; justify-content: space-between; align-items: flex-end; padding: 55px 0 45px; }
.eyebrow { margin: 0; color: var(--green); }
.intro .eyebrow { display: flex; align-items: center; gap: 8px; }
.live-dot, .player-live-dot { width: 7px; height: 7px; display: inline-block; border-radius: 50%; background: var(--orange); }
h1 { margin: 17px 0 13px; font: 500 68px/0.98 var(--serif); letter-spacing: 0; }
h1 em { color: var(--green); font-weight: 400; }
.intro-description { max-width: 390px; margin: 0; color: #676d63; font-size: 14px; line-height: 1.6; }
.intro-stamp { width: 194px; height: 100px; padding: 14px 17px; border: 1px solid #cbd2c8; color: var(--green); display: flex; flex-direction: column; justify-content: space-between; transform: rotate(-3deg); margin: 0 17px 7px 0; }
.stamp-small { font: 9px var(--mono); }
.stamp-large { font: 500 32px/.9 var(--serif); }
.search-panel { background: #e9ece5; padding: 19px 21px 13px; border-top: 2px solid var(--green); }
.search-form { display: grid; grid-template-columns: minmax(190px, 1.4fr) minmax(150px, 1fr) minmax(145px, .9fr) minmax(140px, .8fr) minmax(145px, .9fr) auto; align-items: end; gap: 10px; }
.filter-field { display: flex; min-width: 0; flex-direction: column; gap: 8px; }
.field-label { color: #656b60; }
.input-wrap { position: relative; }
.input-wrap input, .filter-field > input, .filter-field select, .player-block select { height: 43px; width: 100%; border: 1px solid #d5d9d0; border-radius: 0; color: var(--ink); background: #fbfcf9; padding: 0 12px; font-size: 12px; }
.input-wrap input { padding-left: 35px; }
.input-wrap input::placeholder { color: #8b9087; }
.search-icon { position: absolute; left: 12px; top: 8px; color: var(--green); font: 24px/1 var(--serif); }
.search-button { height: 43px; padding: 0 17px; border: 0; color: white; background: var(--green); cursor: pointer; font-size: 12px; font-weight: 600; transition: background 160ms ease; }
.search-button:hover { background: #23684f; }
.search-button:disabled { cursor: wait; opacity: .72; }
.search-button span { padding-right: 5px; font: 19px var(--serif); vertical-align: -1px; }
.search-footnote { display: flex; align-items: center; gap: 10px; margin-top: 12px; color: #73796f; font-size: 9px; }
.footnote-divider { width: 3px; height: 3px; background: var(--orange); border-radius: 50%; }
.clear-button { margin-left: auto; padding: 0; border: 0; color: var(--green); background: none; cursor: pointer; font: 9px var(--mono); text-decoration: underline; text-underline-offset: 3px; }
.listening-layout { display: grid; grid-template-columns: minmax(0, 1.42fr) minmax(310px, .78fr); gap: 42px; padding: 45px 0 60px; align-items: start; }
.results-heading { display: flex; justify-content: space-between; align-items: end; padding-bottom: 15px; border-bottom: 1px solid var(--ink); }
.section-eyebrow { font-size: 9px; }
h2 { margin: 7px 0 0; font: 500 30px/1.05 var(--serif); letter-spacing: 0; }
.result-count { color: var(--muted); font-size: 9px; padding-bottom: 3px; }
.show-list { min-height: 180px; }
.show-row { width: 100%; min-height: 92px; display: grid; grid-template-columns: 27px 58px minmax(0, 1fr) 82px 15px; align-items: center; gap: 13px; padding: 12px 8px 12px 0; color: var(--ink); text-align: left; background: transparent; border: 0; border-bottom: 1px solid var(--line); cursor: pointer; transition: background 140ms ease, padding 140ms ease; }
.show-row:hover, .show-row.selected { background: #e9ece5; padding-left: 8px; }
.row-number { color: #969b91; font-size: 9px; }
.show-art { position: relative; width: 58px; height: 58px; overflow: hidden; background: #dfe4d9; }
.show-art img { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: cover; }
.art-placeholder { position: absolute; inset: 0; display: grid; place-items: center; color: var(--green); font: 11px var(--mono); background: repeating-linear-gradient(135deg, #dce3d6, #dce3d6 5px, #e8ece3 5px, #e8ece3 10px); }
.show-copy { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.show-date { overflow: hidden; color: var(--green); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.show-venue { color: #777c72; }
.show-title { overflow: hidden; font: 500 17px/1.2 var(--serif); text-overflow: ellipsis; white-space: nowrap; }
.show-location { overflow: hidden; color: var(--muted); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.show-rating { justify-self: end; color: var(--ink); text-align: right; font: 11px var(--mono); white-space: nowrap; }
.star { color: var(--orange); }
.show-rating small { display: block; margin-top: 4px; color: var(--muted); font-size: 8px; }
.row-arrow { color: var(--orange); font-size: 14px; }
.status-message { padding: 34px 8px; color: var(--muted); font: 13px var(--serif); }
.error-message { color: #a33f29; }
.pagination { display: flex; align-items: center; justify-content: space-between; padding: 16px 0; }
.pagination button { padding: 7px 0; border: 0; color: var(--green); background: none; cursor: pointer; font: 10px var(--mono); }
.pagination button:disabled { color: #a7aba3; cursor: default; }
.pagination span { color: var(--muted); font-size: 9px; }
.show-panel { position: sticky; top: 18px; padding: 0 0 20px; background: #e9ece5; border-top: 2px solid var(--orange); }
.empty-detail { min-height: 280px; display: grid; place-content: center; justify-items: center; padding: 26px; text-align: center; }
.empty-glyph { color: var(--orange); font: 36px var(--serif); }
.empty-detail p { max-width: 190px; color: #71776d; font: 17px/1.4 var(--serif); }
.detail-art-wrap { position: relative; height: 225px; overflow: hidden; background: #d7dfd2; }
.detail-art { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: cover; }
.detail-art-placeholder { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; color: var(--green); background: repeating-linear-gradient(135deg, #dce3d6, #dce3d6 7px, #e8ece3 7px, #e8ece3 14px); }
.detail-art-placeholder span { font: 9px var(--mono); }
.detail-art-placeholder strong { font: 500 45px/.8 var(--serif); text-align: center; }
.art-caption { position: absolute; z-index: 2; right: 0; bottom: 0; padding: 7px 9px; color: white; background: #20231fd9; font-size: 8px; }
.detail-heading { padding: 20px 21px 17px; border-bottom: 1px solid #d1d7cc; }
.detail-heading h2 { margin-top: 8px; font-size: 25px; }
.detail-meta, .detail-location { margin: 9px 0 0; color: #62685e; font-size: 11px; line-height: 1.4; }
.detail-location { margin-top: 3px; color: var(--muted); }
.detail-rating { display: flex; align-items: center; gap: 6px; margin-top: 14px; font-size: 10px; }
.detail-rating strong { font: 11px var(--mono); }
.detail-rating > span:last-child { color: var(--muted); font-size: 10px; }
.player-block { padding: 16px 21px 17px; border-bottom: 1px solid #d1d7cc; }
.player-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.player-label { display: flex; align-items: center; gap: 7px; color: var(--green); font-size: 9px; }
.player-live-dot { width: 6px; height: 6px; background: #4d8b62; }
.whole-show-button { flex: 0 0 auto; min-height: 32px; display: inline-flex; align-items: center; gap: 7px; padding: 0 10px; border: 0; color: #fff; background: var(--green); font: 9px var(--mono); cursor: pointer; }
.whole-show-button:hover:not(:disabled) { background: #23684f; }
.whole-show-button:disabled { cursor: wait; opacity: .55; }
.whole-show-button span { font-size: 10px; }
.track-list-heading { display: flex; justify-content: space-between; margin: 14px 0 7px; color: #697065; font: 8px var(--mono); }
.track-list-heading span:last-child { color: var(--green); }
.track-list { max-height: 218px; overflow-y: auto; border-top: 1px solid #d1d7cc; border-bottom: 1px solid #d1d7cc; scrollbar-color: #aab8a9 transparent; scrollbar-width: thin; }
.track-row { width: 100%; min-height: 43px; display: grid; grid-template-columns: 22px minmax(0, 1fr) 25px; align-items: center; gap: 8px; padding: 6px 5px; color: var(--ink); background: transparent; border: 0; border-bottom: 1px solid #dce1d8; text-align: left; cursor: pointer; }
.track-row:last-child { border-bottom: 0; }
.track-row:hover, .track-row-active { background: #dce5da; }
.track-play-icon { color: var(--green); font-size: 10px; text-align: center; }
.track-copy { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.track-title { overflow: hidden; font: 13px var(--serif); text-overflow: ellipsis; white-space: nowrap; }
.track-subtitle { color: #747a71; font: 8px var(--mono); }
.track-number { color: #81877e; font: 9px var(--mono); text-align: right; }
.player-block audio { display: block; width: 100%; height: 37px; margin-top: 12px; accent-color: var(--green); }
.player-status { color: #73796f; font: 13px/1.5 var(--serif); }
.archive-item-link { display: inline-block; margin-top: 12px; color: var(--green); font-size: 8px; text-decoration: none; }
.archive-item-link span { color: var(--orange); }
.description-block { padding: 15px 21px 18px; }
.description-block h3 { display: flex; justify-content: space-between; margin: 0 0 9px; color: #62685e; font-size: 9px; font-weight: 400; }
.description-block h3 span { color: var(--orange); }
.description-block p { margin: 0; color: #454b43; font: 13px/1.55 var(--serif); }
.description-block .muted-copy { color: var(--muted); font-style: italic; }
.site-footer { display: flex; justify-content: space-between; gap: 18px; padding: 18px 0 25px; border-top: 1px solid var(--line); color: #6f756b; font-size: 8px; }
.site-footer a { color: var(--green); text-decoration: none; }
.footer-dot { padding: 0 6px; color: var(--orange); }

@keyframes arrive { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 980px) {
  .app-shell { padding: 0 4.5%; }
  .search-form { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .search-button { grid-column: 1 / -1; }
  .listening-layout { grid-template-columns: minmax(0, 1fr) minmax(280px, .85fr); gap: 24px; }
  .show-row { grid-template-columns: 20px 48px minmax(0, 1fr) 66px 12px; gap: 9px; }
  .show-art { width: 48px; height: 48px; }
  .show-title { font-size: 15px; }
}
@media (max-width: 720px) {
  .app-shell { padding: 0 20px; }
  .masthead { height: 62px; }
  .archive-link { font-size: 9px; }
  .intro { padding: 39px 0 31px; }
  h1 { font-size: 53px; }
  .intro-description { max-width: 310px; font-size: 13px; }
  .intro-stamp { width: 150px; height: 82px; margin-right: 0; padding: 11px; }
  .stamp-large { font-size: 26px; }
  .stamp-small { font-size: 7px; }
  .search-panel { padding: 16px; }
  .search-form { grid-template-columns: 1fr 1fr; }
  .song-field, .venue-field { grid-column: 1 / -1; }
  .search-button { grid-column: 1 / -1; }
  .search-footnote { flex-wrap: wrap; font-size: 8px; }
  .listening-layout { grid-template-columns: 1fr; gap: 29px; padding: 34px 0 43px; }
  .show-panel { position: static; }
  .detail-art-wrap { height: min(58vw, 280px); }
  .show-row { grid-template-columns: 18px 48px minmax(0, 1fr) 62px; gap: 9px; }
  .row-arrow { display: none; }
  .show-rating { font-size: 10px; }
}
@media (max-width: 440px) {
  .app-shell { padding: 0 15px; }
  .intro { align-items: flex-start; }
  .intro-stamp { width: 112px; height: 72px; margin-top: 39px; padding: 8px; }
  .stamp-large { font-size: 21px; }
  .stamp-small { font-size: 6px; }
  h1 { font-size: 46px; }
  .intro-description { max-width: 230px; font-size: 12px; }
  .search-form { grid-template-columns: 1fr; gap: 11px; }
  .song-field, .venue-field, .search-button { grid-column: auto; }
  .search-footnote { gap: 7px; }
  .show-row { grid-template-columns: 15px 42px minmax(0, 1fr) 54px; gap: 7px; padding-right: 2px; }
  .show-art { width: 42px; height: 42px; }
  .show-title { font-size: 14px; }
  .show-date, .show-location { font-size: 8px; }
  .show-rating { font-size: 9px; }
  .show-rating small { font-size: 7px; }
  .site-footer { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
</style>