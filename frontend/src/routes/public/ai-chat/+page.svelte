<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { AlertCircle, Bot, RotateCcw, Send, Sparkles, User } from 'lucide-svelte';
	import { sendPublicMessage } from './chat.remote';
	import {
		PublicChatUnavailableError,
		type PublicChatMessageOut
	} from './chat.types';

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

	const CHAT_ID_STORAGE_KEY = 'public-ai-chat:chat-id';

	let messages = $state<Message[]>([WELCOME]);
	let draft = $state('');
	let isThinking = $state(false);
	let errorText = $state<string | null>(null);
	let chatId = $state<string | null>(null);
	let listEl = $state<HTMLDivElement | null>(null);
	let textareaEl = $state<HTMLTextAreaElement | null>(null);
	let nextId = 1;

	const canSend = $derived(draft.trim().length > 0 && !isThinking);

	function toUiMessage(m: PublicChatMessageOut): Message {
		return {
			id: nextId++,
			role: m.role === 'assistant' ? 'assistant' : 'user',
			text: m.content,
			at: Date.parse(m.created_at) || Date.now()
		};
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

	function readStoredChatId(): string | null {
		try {
			return window.localStorage.getItem(CHAT_ID_STORAGE_KEY);
		} catch {
			return null;
		}
	}

	function writeStoredChatId(value: string | null) {
		try {
			if (value === null) {
				window.localStorage.removeItem(CHAT_ID_STORAGE_KEY);
			} else {
				window.localStorage.setItem(CHAT_ID_STORAGE_KEY, value);
			}
		} catch {
			/* localStorage may be disabled (private mode); fall back silently */
		}
	}

	function reset() {
		messages = [WELCOME];
		draft = '';
		isThinking = false;
		errorText = null;
		chatId = null;
		writeStoredChatId(null);
		scrollToBottom();
		textareaEl?.focus();
	}

	onMount(() => {
		chatId = readStoredChatId();
	});

	async function send() {
		const text = draft.trim();
		if (!text || isThinking) return;

		errorText = null;
		draft = '';
		isThinking = true;
		scrollToBottom();

		try {
			const reply = await sendPublicMessage({ chat_id: chatId, content: text });
			chatId = reply.chat_id;
			writeStoredChatId(reply.chat_id);
			messages = [
				...messages,
				toUiMessage(reply.user_message),
				toUiMessage(reply.assistant_message)
			];
		} catch (err) {
			const fallbackChatId = err instanceof PublicChatUnavailableError ? err.chatId : null;
			if (fallbackChatId && fallbackChatId !== chatId) {
				chatId = fallbackChatId;
				writeStoredChatId(fallbackChatId);
			}
			const detail =
				err instanceof PublicChatUnavailableError
					? err.message
					: 'The assistant is unreachable right now. Please try again in a moment.';
			errorText = detail;
			messages = [
				...messages,
				{
					id: nextId++,
					role: 'assistant',
					text: `Sorry, I couldn't reach the assistant. ${detail}`,
					at: Date.now()
				}
			];
		} finally {
			isThinking = false;
			scrollToBottom();
			textareaEl?.focus();
		}
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
		<button
			type="button"
			class="btn-icon btn preset-tonal-surface"
			aria-label="Reset conversation"
			title="Reset conversation"
			onclick={reset}
		>
			<RotateCcw size={16} strokeWidth={1.75} />
		</button>
	</header>

	{#if errorText}
		<div
			role="alert"
			class="alert preset-tonal-error flex items-start gap-2 p-3 text-sm"
		>
			<AlertCircle size={16} strokeWidth={1.75} class="mt-0.5 shrink-0" />
			<span>{errorText}</span>
		</div>
	{/if}

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
