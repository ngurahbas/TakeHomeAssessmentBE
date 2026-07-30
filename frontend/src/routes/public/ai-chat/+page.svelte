<script lang="ts">
	import { tick } from 'svelte';
	import { Bot, RotateCcw, Send, Sparkles, User } from 'lucide-svelte';

	type Role = 'user' | 'assistant';

	type Message = {
		id: number;
		role: Role;
		text: string;
		at: number;
	};

	const WELCOME: Message = {
		id: 0,
		role: 'assistant',
		text: "Hi! I'm the Real Estate AI Assistant. Ask me about available properties, book a viewing, or request help from a human agent.",
		at: Date.now()
	};

	const REPLIES = [
		"I can search for 2-bedroom apartments in your area. What's your price range?",
		"I found 3 properties that match. Would you like to schedule a viewing?",
		"Booking a viewing for Saturday at 2:00 PM. Please confirm the property address.",
		"Let me connect you to a human agent — they'll be with you shortly.",
		"Our office hours are 9:00 AM to 7:00 PM, Monday through Saturday.",
		"Parking is included with most of our listings. Pets are welcome with a small deposit."
	];

	let messages = $state<Message[]>([WELCOME]);
	let draft = $state('');
	let isThinking = $state(false);
	let listEl = $state<HTMLDivElement | null>(null);
	let textareaEl = $state<HTMLTextAreaElement | null>(null);
	let nextId = 1;

	const canSend = $derived(draft.trim().length > 0 && !isThinking);

	function pickReply(): string {
		return REPLIES[Math.floor(Math.random() * REPLIES.length)];
	}

	function autoGrow(node: HTMLTextAreaElement) {
		const fit = () => {
			node.style.height = 'auto';
			node.style.height = `${Math.min(node.scrollHeight, 160)}px`;
		};
		fit();
		node.addEventListener('input', fit);
		return {
			destroy() {
				node.removeEventListener('input', fit);
			}
		};
	}

	async function scrollToBottom() {
		await tick();
		if (listEl) {
			listEl.scrollTop = listEl.scrollHeight;
		}
	}

	function reset() {
		messages = [WELCOME];
		draft = '';
		isThinking = false;
		scrollToBottom();
		textareaEl?.focus();
	}

	async function send() {
		const text = draft.trim();
		if (!text || isThinking) return;

		messages = [...messages, { id: nextId++, role: 'user', text, at: Date.now() }];
		draft = '';
		isThinking = true;
		scrollToBottom();

		const delay = 700 + Math.random() * 500;
		setTimeout(() => {
			messages = [
				...messages,
				{ id: nextId++, role: 'assistant', text: pickReply(), at: Date.now() }
			];
			isThinking = false;
			scrollToBottom();
		}, delay);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}

	function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		send();
	}

	function formatTime(at: number): string {
		const d = new Date(at);
		const hh = d.getHours().toString().padStart(2, '0');
		const mm = d.getMinutes().toString().padStart(2, '0');
		return `${hh}:${mm}`;
	}
</script>

<svelte:head>
	<title>AI Chat · Real Estate AI Assistant</title>
</svelte:head>

<section class="mx-auto flex h-screen max-w-3xl flex-col gap-4 p-4 sm:p-6">
	<header class="card preset-filled-surface-100-900 flex items-center justify-between gap-3 p-4">
		<div class="flex items-center gap-3">
			<span
				class="bg-primary-500/15 text-primary-500 grid h-10 w-10 place-items-center rounded-full"
			>
				<Sparkles size={18} strokeWidth={1.75} />
			</span>
			<div class="space-y-0.5">
				<h1 class="h3 leading-none">AI Chat</h1>
				<p class="text-xs opacity-60">Real Estate AI Assistant</p>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<span
				class="badge preset-tonal-warning text-[10px] uppercase tracking-wider"
				title="This page is a UI preview and is not connected to the backend."
			>
				Preview · not connected
			</span>
			<button
				type="button"
				class="btn-icon btn preset-tonal-surface"
				aria-label="Reset conversation"
				title="Reset conversation"
				onclick={reset}
			>
				<RotateCcw size={16} strokeWidth={1.75} />
			</button>
		</div>
	</header>

	<div
		bind:this={listEl}
		class="card preset-filled-surface-50-950 flex-1 space-y-4 overflow-y-auto p-4"
	>
		{#each messages as m (m.id)}
			{#if m.role === 'user'}
				<div class="flex items-end justify-end gap-2">
					<div class="flex max-w-[80%] flex-col items-end gap-1">
						<div class="bg-primary-500 text-primary-contrast-500 rounded-2xl rounded-br-sm px-4 py-2 whitespace-pre-wrap break-words">
							{m.text}
						</div>
						<span class="text-[10px] opacity-50">{formatTime(m.at)}</span>
					</div>
					<span
						class="bg-primary-500/15 text-primary-500 grid h-8 w-8 shrink-0 place-items-center rounded-full"
					>
						<User size={14} strokeWidth={1.75} />
					</span>
				</div>
			{:else}
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
							{m.text}
						</div>
						<span class="text-[10px] opacity-50">{formatTime(m.at)}</span>
					</div>
				</div>
			{/if}
		{/each}

		{#if isThinking}
			<div class="flex items-end gap-2">
				<span
					class="preset-tonal-surface text-surface-950-50 grid h-8 w-8 shrink-0 place-items-center rounded-full"
				>
					<Bot size={14} strokeWidth={1.75} />
				</span>
				<div
					class="card preset-tonal-surface border-surface-200-800 flex items-center gap-1.5 rounded-2xl rounded-bl-sm border px-4 py-3"
				>
					<span class="bg-surface-500 inline-block h-2 w-2 animate-bounce rounded-full [animation-delay:-0.3s]"></span>
					<span class="bg-surface-500 inline-block h-2 w-2 animate-bounce rounded-full [animation-delay:-0.15s]"></span>
					<span class="bg-surface-500 inline-block h-2 w-2 animate-bounce rounded-full"></span>
				</div>
			</div>
		{/if}
	</div>

	<form
		onsubmit={onSubmit}
		class="card preset-filled-surface-100-900 flex items-end gap-2 p-3"
	>
		<textarea
			bind:this={textareaEl}
			bind:value={draft}
			use:autoGrow
			onkeydown={onKeydown}
			class="textarea flex-1 resize-none rounded-md border-0 bg-transparent focus:ring-0"
			rows="1"
			placeholder="Type a message — Enter to send, Shift+Enter for newline"
			aria-label="Message"
		></textarea>
		<button
			type="submit"
			class="btn preset-filled-primary-500"
			disabled={!canSend}
			aria-label="Send message"
		>
			<Send size={16} strokeWidth={1.75} />
			<span class="hidden sm:inline">Send</span>
		</button>
	</form>
</section>
