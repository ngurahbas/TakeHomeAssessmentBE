export type PublicChatRole = 'system' | 'user' | 'assistant';

export type PublicChatMessageOut = {
	id: number;
	role: PublicChatRole;
	content: string;
	created_at: string;
};

export type PublicChatSendRequest = {
	chat_id?: string | null;
	content: string;
};

export type PublicChatSendResponse = {
	chat_id: string;
	user_message: PublicChatMessageOut;
	assistant_message: PublicChatMessageOut;
};

export type PublicChatSession = {
	id: string;
	created_at: string;
	last_active_at: string;
	messages: PublicChatMessageOut[];
};

export class PublicChatUnavailableError extends Error {
	readonly status: number;
	readonly chatId: string | null;

	constructor(status: number, message?: string, chatId: string | null = null) {
		super(message ?? 'AI chat is temporarily unavailable');
		this.name = 'PublicChatUnavailableError';
		this.status = status;
		this.chatId = chatId;
	}
}
