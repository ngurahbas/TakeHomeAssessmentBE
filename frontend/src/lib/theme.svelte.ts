export type ColorMode = 'light' | 'dark' | 'system';
export type ResolvedMode = 'light' | 'dark';

export const THEMES = [
	'cerberus',
	'catppuccin',
	'concord',
	'crimson',
	'dracula',
	'fennec',
	'hamlindigo',
	'legacy',
	'mint',
	'modern',
	'mona',
	'nosh',
	'nouveau',
	'pine',
	'reign',
	'rocket',
	'rose',
	'rosepine',
	'sahara',
	'seafoam',
	'terminus',
	'vintage',
	'vox',
	'wintry'
] as const;
export type ThemeName = (typeof THEMES)[number];

const DEFAULT_THEME: ThemeName = 'cerberus';

const MODE_KEY = 'mode';
const THEME_KEY = 'theme';

function isColorMode(v: unknown): v is ColorMode {
	return v === 'light' || v === 'dark' || v === 'system';
}

function isThemeName(v: unknown): v is ThemeName {
	return typeof v === 'string' && (THEMES as readonly string[]).includes(v);
}

function readMode(): ColorMode {
	if (typeof window === 'undefined') return 'system';
	try {
		const v = window.localStorage.getItem(MODE_KEY);
		return isColorMode(v) ? v : 'system';
	} catch {
		return 'system';
	}
}

function writeMode(mode: ColorMode): void {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(MODE_KEY, mode);
	} catch {
		/* private mode / quota — best effort */
	}
}

function readTheme(): ThemeName {
	if (typeof window === 'undefined') return DEFAULT_THEME;
	try {
		const v = window.localStorage.getItem(THEME_KEY);
		return isThemeName(v) ? v : DEFAULT_THEME;
	} catch {
		return DEFAULT_THEME;
	}
}

function writeTheme(theme: ThemeName): void {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(THEME_KEY, theme);
	} catch {
		/* best effort */
	}
}

let mode = $state<ColorMode>('system');
let theme = $state<ThemeName>(DEFAULT_THEME);
let systemPrefersDark = $state(false);
let initialized = false;
let mql: MediaQueryList | null = null;
let onChange: ((e: MediaQueryListEvent) => void) | null = null;

const resolved = $derived<ResolvedMode>(
	mode === 'system' ? (systemPrefersDark ? 'dark' : 'light') : mode
);

function applyModeToDom(r: ResolvedMode): void {
	if (typeof document === 'undefined') return;
	document.documentElement.classList.toggle('dark', r === 'dark');
}

function applyThemeToDom(t: ThemeName): void {
	if (typeof document === 'undefined') return;
	document.documentElement.setAttribute('data-theme', t);
}

export function init(): void {
	if (initialized || typeof window === 'undefined') return;
	initialized = true;

	mode = readMode();
	theme = readTheme();
	systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

	mql = window.matchMedia('(prefers-color-scheme: dark)');
	onChange = (e) => {
		systemPrefersDark = e.matches;
		applyModeToDom(resolved);
	};
	mql.addEventListener('change', onChange);

	applyModeToDom(resolved);
	applyThemeToDom(theme);
}

export function setMode(m: ColorMode): void {
	mode = m;
	writeMode(m);
	applyModeToDom(resolved);
}

export function cycle(): void {
	const next: ColorMode = mode === 'system' ? 'light' : mode === 'light' ? 'dark' : 'system';
	setMode(next);
}

export function getMode(): ColorMode {
	return mode;
}

export function getResolved(): ResolvedMode {
	return resolved;
}

export function setTheme(t: ThemeName): void {
	theme = t;
	writeTheme(t);
	applyThemeToDom(theme);
}

export function getTheme(): ThemeName {
	return theme;
}
