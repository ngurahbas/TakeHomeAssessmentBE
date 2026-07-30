<script lang="ts">
	import { ArrowLeft, Clipboard, MessageSquareWarning, MessageCircle, ScrollText } from 'lucide-svelte';
	import type { AiEscalationDetail } from '../ai-escalations.types';
	import EscalationChatTranscript from './_components/EscalationChatTranscript.svelte';

	let {
		data
	}: {
		data: { detail: AiEscalationDetail };
	} = $props();

	const detail = $derived(data.detail);
	const messageCount = $derived(detail.session.messages.length);

	let copied = $state(false);

	function formatDateTime(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toISOString().replace('T', ' ').slice(0, 16);
	}

	async function copyChatId() {
		try {
			await navigator.clipboard.writeText(detail.public_chat_id);
			copied = true;
			setTimeout(() => (copied = false), 1500);
		} catch {
			copied = false;
		}
	}
</script>

<svelte:head>
	<title>Escalation #{detail.id} · Real Estate AI</title>
</svelte:head>

<section class="space-y-6">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex items-start gap-3">
			<a
				href="/dashboard/ai-escalations"
				class="btn-icon btn-icon-sm preset-tonal-surface"
				aria-label="Back to escalations"
			>
				<ArrowLeft size={16} strokeWidth={1.75} />
			</a>
			<div>
				<div class="flex items-center gap-2">
					<h1 class="h2 leading-tight">Escalation #{detail.id}</h1>
					<span class="badge preset-tonal-warning text-[10px]">Needs human attention</span>
				</div>
				<p class="opacity-70 mt-1 text-sm">
					Created {formatDateTime(detail.created_at)}
				</p>
			</div>
		</div>
	</header>

	<div class="grid gap-4 lg:grid-cols-[1fr_18rem]">
		<div class="space-y-4">
			<div class="card preset-filled-surface-100-900 space-y-3 p-5">
				<div class="flex items-center gap-2">
					<ScrollText size={16} strokeWidth={1.75} class="opacity-70" />
					<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Public chat transcript</p>
				</div>
				<EscalationChatTranscript session={detail.session} />
			</div>
		</div>

		<aside class="space-y-4">
			<div class="card preset-filled-surface-100-900 space-y-2 p-5">
				<div class="flex items-center gap-2">
					<MessageSquareWarning size={14} strokeWidth={1.75} class="opacity-70" />
					<p class="text-xs font-semibold tracking-wider uppercase opacity-60">User intention</p>
				</div>
				<p class="text-sm leading-relaxed whitespace-pre-line">
					{detail.user_intention}
				</p>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-2 p-5 text-sm">
				<div class="flex items-center gap-2">
					<MessageCircle size={14} strokeWidth={1.75} class="opacity-70" />
					<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Public chat</p>
				</div>
				<div class="flex items-center justify-between gap-2">
					<code
						class="bg-surface-200-800 text-xs break-all rounded px-2 py-1 font-mono"
					>
						{detail.public_chat_id}
					</code>
					<button
						type="button"
						class="btn btn-sm preset-tonal-surface"
						onclick={copyChatId}
						aria-label="Copy public chat id"
					>
						<Clipboard size={14} strokeWidth={1.75} />
						<span>{copied ? 'Copied' : 'Copy'}</span>
					</button>
				</div>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-2 p-5 text-sm">
				<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Session</p>
				<p>
					<span class="opacity-60">Started:</span>
					{formatDateTime(detail.session.created_at)}
				</p>
				<p>
					<span class="opacity-60">Last active:</span>
					{formatDateTime(detail.session.last_active_at)}
				</p>
				<p>
					<span class="opacity-60">Message count:</span>
					{messageCount}
				</p>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-1 p-5 text-xs">
				<p class="font-semibold tracking-wider uppercase opacity-60">Audit</p>
				<p>Escalation ID: {detail.id}</p>
				<p>Public chat ID: {detail.public_chat_id}</p>
			</div>
		</aside>
	</div>
</section>
