export type User = {
	id: number;
	email: string;
	role: string;
};

export type LoginResponse = {
	token: string;
	user: User;
};
