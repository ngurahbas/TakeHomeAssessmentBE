<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { Bot, Settings2, User } from 'lucide-svelte';
	import type { PublicChatSession } from '../../../../public/ai-chat/chat.types';

	let { session }: { session: PublicChatSession } = $props();

	let listEl = $state<HTMLDivElement | null>(null);

	const orderedMessages = $derived([...session.messages]);

	function formatTime(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return '';
		const hh = d.getHours().toString().padStart(2, '0');
		const mm = d.getMinutes().toString().padStart(2, '0');
		return `${hh}:${mm}`;
	}

	function roleLabel(role: string): string {
		if (role === 'user') return 'You';
		if (role === 'assistant') return 'Assistant';
		return 'System';
	}

	onMount(async () => {
		await tick();
		if (listEl) {
			listEl.scrollTop = listEl.scrollHeight;
		}
	});
</script>

<div
	bind:this={listEl}
	class="card preset-filled-surface-50-950 max-h-[32rem] space-y-4 overflow-y-auto p-4"
>
	{#if orderedMessages.length === 0}
		<p class="text-sm opacity-60">No messages in this session.</p>
	{:else}
		{#each orderedMessages as m (m.id)}
			{#if m.role === 'user'}
				<div class="flex items-end justify-end gap-2">
					<div class="flex max-w-[80%] flex-col items-end gap-1">
						<div
							class="bg-primary-500 text-primary-contrast-500 rounded-2xl rounded-br-sm px-4 py-2 whitespace-pre-wrap break-words"
						>
							{m.content}
						</div>
						<span class="text-[10px] opacity-50">{formatTime(m.created_at)}</span>
					</div>
					<span
						class="bg-primary-500/15 text-primary-500 grid h-8 w-8 shrink-0 place-items-center rounded-full"
					>
						<User size={14} strokeWidth={1.75} />
					</span>
				</div>
			{:else if m.role === 'assistant'}
				<div class="flex items-end gap-2">
					<span
						class="preset-tonal-surface text-surface-950-50 grid h-8 w-8 shrink-0 place-items-center rounded-full"
					>
						<Bot size={14} strokeWidth={1.75} />
					</span>
					<div class="flex max-w-[80%] flex-col gap-1">
						<div
							class="card preset-tonal-surface border-surface-200-800 rounded-2xl rounded-bl-sm border px-4 py-2 whitespace-pre-wrap break-words"
						>
							{m.content}
						</div>
						<span class="text-[10px] opacity-50">{formatTime(m.created_at)}</span>
					</div>
				</div>
			{:else}
				<div class="flex items-end gap-2">
					<span
						class="bg-surface-500/15 text-surface-700-300 grid h-8 w-8 shrink-0 place-items-center rounded-full"
					>
						<Settings2 size={14} strokeWidth={1.75} />
					</span>
					<div class="flex max-w-[80%] flex-col gap-1">
						<div
							class="card preset-tonal-surface border-surface-200-800 rounded-2xl rounded-bl-sm border px-4 py-2 text-xs whitespace-pre-wrap break-words opacity-80"
						>
							<span class="text-[10px] font-semibold tracking-wider uppercase opacity-60">
								{roleLabel(m.role)}
							</span>
							<p class="mt-1">{m.content}</p>
						</div>
						<span class="text-[10px] opacity-50">{formatTime(m.created_at)}</span>
					</div>
				</div>
			{/if}
		{/each}
	{/if}
</div>
