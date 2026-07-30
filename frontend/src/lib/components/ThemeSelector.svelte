<script lang="ts">
	import { Menu } from '@skeletonlabs/skeleton-svelte';
	import { Check, Palette } from 'lucide-svelte';
	import { getTheme, setTheme, THEMES, type ThemeName } from '$lib/theme.svelte';

	type Option = { value: ThemeName; swatch: string };

	const swatches: Record<ThemeName, string> = {
		cerberus: 'oklch(0.57 0.21 258.29)',
		catppuccin: 'oklch(0.66 0.18 273.14)',
		concord: 'oklch(0.58 0.21 273.85)',
		crimson: 'oklch(0.56 0.21 19.55)',
		dracula: 'oklch(0.74 0.15 302.13)',
		fennec: 'oklch(0.66 0.21 38.25)',
		hamlindigo: 'oklch(0.8 0.08 266.51)',
		legacy: 'oklch(0.7 0.15 162.21)',
		mint: 'oklch(0.84 0.18 148.98)',
		modern: 'oklch(0.66 0.21 354.32)',
		mona: 'oklch(0.56 0.21 294.98)',
		nosh: 'oklch(0.56 0.23 24.62)',
		nouveau: 'oklch(0.83 0.16 97)',
		pine: 'oklch(0.62 0.08 79.85)',
		reign: 'oklch(0.95 0.17 110.7)',
		rocket: 'oklch(0.71 0.13 215.21)',
		rose: 'oklch(0.7 0.13 348.12)',
		rosepine: 'oklch(0.53 0.08 227.38)',
		sahara: 'oklch(0.78 0.15 76.87)',
		seafoam: 'oklch(0.81 0.07 190.34)',
		terminus: 'oklch(0.49 0.3 279.02)',
		vintage: 'oklch(0.71 0.16 59.66)',
		vox: 'oklch(0.83 0.1 51.5)',
		wintry: 'oklch(0.62 0.19 259.81)'
	};

	const options: Option[] = THEMES.map((t) => ({ value: t, swatch: swatches[t] }));

	const current = $derived(getTheme());
</script>

<Menu
	positioning={{ placement: 'bottom-end' }}
	onSelect={(d) => setTheme(d.value as ThemeName)}
>
	<Menu.Trigger
		class="btn-icon btn preset-tonal-surface"
		aria-label={`Theme: ${current}`}
		title={`Theme: ${current}`}
	>
		<Palette size={18} strokeWidth={1.75} />
	</Menu.Trigger>
	<Menu.Positioner>
		<Menu.Content class="card preset-tonal-surface w-56 max-h-96 overflow-y-auto p-1.5 shadow-xl">
			<Menu.ItemGroup>
				<Menu.ItemGroupLabel class="px-2 pt-1 pb-2 text-xs uppercase tracking-wider opacity-60">
					Theme
				</Menu.ItemGroupLabel>
				{#each options as opt (opt.value)}
					<Menu.Item
						value={opt.value}
						class="flex items-center gap-2 rounded px-2 py-1.5 text-sm capitalize hover:preset-tonal-primary data-[highlighted]:preset-tonal-primary"
					>
						<span
							class="inline-block h-4 w-4 shrink-0 rounded-full border border-surface-200-800"
							style="background-color: {opt.swatch}"
						></span>
						<span class="flex-1">{opt.value}</span>
						{#if current === opt.value}
							<Check size={14} strokeWidth={2.5} class="text-primary-500" />
						{/if}
					</Menu.Item>
				{/each}
			</Menu.ItemGroup>
		</Menu.Content>
	</Menu.Positioner>
</Menu>
