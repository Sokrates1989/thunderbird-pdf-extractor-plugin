/** Minimal Thunderbird 128 API declarations used by this extension. */

interface ThunderbirdMessageHeader {
  readonly author: string;
  readonly ccList?: readonly string[];
  readonly date: Date;
  readonly headerMessageId?: string;
  readonly id: number;
  readonly recipients?: readonly string[];
  readonly size?: number;
  readonly subject: string;
}

interface ThunderbirdMessageList {
  readonly id?: string;
  readonly messages: readonly ThunderbirdMessageHeader[];
}

interface ThunderbirdAttachment {
  readonly contentId?: string | null;
  readonly contentDisposition?: "attachment" | "inline" | null;
  readonly contentType: string;
  readonly name: string;
  readonly partName?: string;
  readonly size: number;
}

interface ThunderbirdTab {
  readonly id?: number;
}

interface ThunderbirdNativePort {
  readonly error?: Error;
  readonly onDisconnect: {
    addListener(listener: (port: ThunderbirdNativePort) => void): void;
    removeListener(listener: (port: ThunderbirdNativePort) => void): void;
  };
  readonly onMessage: {
    addListener(listener: (message: unknown) => void): void;
    removeListener(listener: (message: unknown) => void): void;
  };
  disconnect(): void;
  postMessage(message: object): void;
}

interface ThunderbirdMenuClickInfo {
  readonly menuItemId: string | number;
  readonly selectedMessages?: ThunderbirdMessageList;
}

interface ThunderbirdApi {
  readonly i18n: {
    getMessage(messageName: string, substitutions?: string | readonly string[]): string;
    getUILanguage(): string;
  };
  readonly menus: {
    create(createProperties: {
      readonly contexts: readonly string[];
      readonly id: string;
      readonly title: string;
    }): Promise<string | number>;
    readonly onClicked: {
      addListener(listener: (info: ThunderbirdMenuClickInfo, tab: ThunderbirdTab) => void): void;
    };
    remove(menuItemId: string): Promise<void>;
  };
  readonly messageDisplay: {
    getDisplayedMessages(tabId?: number): Promise<ThunderbirdMessageList>;
  };
  readonly messages: {
    get(messageId: number): Promise<ThunderbirdMessageHeader>;
    getRaw(
      messageId: number,
      options: { readonly data_format: "File"; readonly decrypt: boolean },
    ): Promise<File>;
    listAttachments(messageId: number): Promise<readonly ThunderbirdAttachment[]>;
  };
  readonly runtime: {
    readonly id: string;
    connectNative(application: string): ThunderbirdNativePort;
    getManifest(): { readonly version: string };
    getURL(path: string): string;
    readonly onInstalled: {
      addListener(listener: () => void): void;
    };
    readonly onMessage: {
      addListener(listener: (message: unknown) => void | Promise<void>): void;
    };
    openOptionsPage(): Promise<void>;
    sendMessage(message: object): Promise<unknown>;
  };
  readonly storage: {
    readonly local: {
      get(keys?: string | readonly string[] | object | null): Promise<Record<string, unknown>>;
      set(items: Record<string, unknown>): Promise<void>;
    };
  };
  readonly tabs: {
    query(queryInfo: { readonly active: boolean; readonly currentWindow: boolean }): Promise<readonly ThunderbirdTab[]>;
  };
  readonly windows: {
    create(createData: {
      readonly height?: number;
      readonly type?: "popup";
      readonly url: string;
      readonly width?: number;
    }): Promise<unknown>;
  };
}

declare const browser: ThunderbirdApi;
