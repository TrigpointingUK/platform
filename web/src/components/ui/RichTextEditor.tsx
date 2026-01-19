import { useEditor, EditorContent, Editor, Extension } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { TextStyle } from "@tiptap/extension-text-style";
import { Color } from "@tiptap/extension-color";
import { useCallback, useEffect, useState } from "react";

// Custom font size extension
const FontSize = Extension.create({
  name: "fontSize",

  addOptions() {
    return {
      types: ["textStyle"],
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) =>
              element.style.fontSize?.replace(/['"]+/g, ""),
            renderHTML: (attributes) => {
              if (!attributes.fontSize) {
                return {};
              }
              return {
                style: `font-size: ${attributes.fontSize}`,
              };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      setFontSize:
        (fontSize: string) =>
        ({ chain }) => {
          return chain().setMark("textStyle", { fontSize }).run();
        },
      unsetFontSize:
        () =>
        ({ chain }) => {
          return chain()
            .setMark("textStyle", { fontSize: null })
            .removeEmptyTextStyle()
            .run();
        },
    } as const;
  },
});

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  className?: string;
}

interface MenuBarProps {
  editor: Editor | null;
}

const FONT_SIZES = [
  { name: "Small", value: "0.875rem" },
  { name: "Normal", value: null },
  { name: "Large", value: "1.25rem" },
  { name: "X-Large", value: "1.5rem" },
];

const PRESET_COLOURS = [
  { name: "Red", value: "#dc2626" },
  { name: "Orange", value: "#ea580c" },
  { name: "Amber", value: "#d97706" },
  { name: "Green", value: "#16a34a" },
  { name: "Blue", value: "#2563eb" },
  { name: "Purple", value: "#9333ea" },
  { name: "Black", value: "#000000" },
];

function MenuBar({ editor }: MenuBarProps) {
  const [showColourPicker, setShowColourPicker] = useState(false);
  const [showFontSizePicker, setShowFontSizePicker] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const [showLinkInput, setShowLinkInput] = useState(false);

  const setLink = useCallback(() => {
    if (!editor) return;

    if (linkUrl === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      setShowLinkInput(false);
      return;
    }

    // Add https:// if no protocol specified
    const url = linkUrl.match(/^https?:\/\//) ? linkUrl : `https://${linkUrl}`;

    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .setLink({ href: url })
      .run();

    setLinkUrl("");
    setShowLinkInput(false);
  }, [editor, linkUrl]);

  const openLinkInput = useCallback(() => {
    if (!editor) return;
    const previousUrl = editor.getAttributes("link").href || "";
    setLinkUrl(previousUrl);
    setShowLinkInput(true);
  }, [editor]);

  if (!editor) {
    return null;
  }

  const buttonClass = (isActive: boolean) =>
    `px-2 py-1 rounded text-sm font-medium transition-colors ${
      isActive
        ? "bg-trig-green-600 text-white"
        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
    }`;

  return (
    <div className="flex flex-wrap items-center gap-1 p-2 border-b border-gray-200 bg-gray-50 rounded-t-md">
      {/* Text formatting */}
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={buttonClass(editor.isActive("bold"))}
        title="Bold"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={buttonClass(editor.isActive("italic"))}
        title="Italic"
      >
        <em>I</em>
      </button>

      <div className="w-px h-6 bg-gray-300 mx-1" />

      {/* Link */}
      {showLinkInput ? (
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                setLink();
              }
              if (e.key === "Escape") {
                setShowLinkInput(false);
                setLinkUrl("");
              }
            }}
            placeholder="Enter URL..."
            className="px-2 py-1 text-sm border border-gray-300 rounded w-48 focus:outline-none focus:ring-1 focus:ring-trig-green-500"
            autoFocus
          />
          <button
            type="button"
            onClick={setLink}
            className="px-2 py-1 text-sm bg-trig-green-600 text-white rounded hover:bg-trig-green-700"
          >
            Set
          </button>
          <button
            type="button"
            onClick={() => {
              setShowLinkInput(false);
              setLinkUrl("");
            }}
            className="px-2 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            Cancel
          </button>
        </div>
      ) : (
        <>
          <button
            type="button"
            onClick={openLinkInput}
            className={buttonClass(editor.isActive("link"))}
            title="Add link"
          >
            🔗
          </button>
          {editor.isActive("link") && (
            <button
              type="button"
              onClick={() => editor.chain().focus().unsetLink().run()}
              className="px-2 py-1 rounded text-sm font-medium bg-red-100 text-red-700 hover:bg-red-200"
              title="Remove link"
            >
              ✕
            </button>
          )}
        </>
      )}

      <div className="w-px h-6 bg-gray-300 mx-1" />

      {/* Colour picker */}
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            setShowColourPicker(!showColourPicker);
            setShowFontSizePicker(false);
          }}
          className={`px-2 py-1 rounded text-sm font-medium transition-colors ${
            showColourPicker
              ? "bg-trig-green-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
          title="Text colour"
        >
          <span
            style={{
              color: editor.getAttributes("textStyle").color || "#000000",
            }}
          >
            A
          </span>
          <span className="ml-1 text-xs">▼</span>
        </button>

        {showColourPicker && (
          <div className="absolute top-full left-0 mt-1 p-2 bg-white border border-gray-200 rounded-md shadow-lg z-10">
            <div className="grid grid-cols-4 gap-1">
              {PRESET_COLOURS.map((colour) => (
                <button
                  key={colour.value}
                  type="button"
                  onClick={() => {
                    editor.chain().focus().setColor(colour.value).run();
                    setShowColourPicker(false);
                  }}
                  className="w-6 h-6 rounded border border-gray-300 hover:scale-110 transition-transform"
                  style={{ backgroundColor: colour.value }}
                  title={colour.name}
                />
              ))}
              <button
                type="button"
                onClick={() => {
                  editor.chain().focus().unsetColor().run();
                  setShowColourPicker(false);
                }}
                className="w-6 h-6 rounded border border-gray-300 bg-white hover:bg-gray-100 text-xs"
                title="Remove colour"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Font size picker */}
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            setShowFontSizePicker(!showFontSizePicker);
            setShowColourPicker(false);
          }}
          className={`px-2 py-1 rounded text-sm font-medium transition-colors ${
            showFontSizePicker
              ? "bg-trig-green-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
          title="Font size"
        >
          <span className="text-xs">Size</span>
          <span className="ml-1 text-xs">▼</span>
        </button>

        {showFontSizePicker && (
          <div className="absolute top-full left-0 mt-1 p-1 bg-white border border-gray-200 rounded-md shadow-lg z-10 min-w-[100px]">
            {FONT_SIZES.map((size) => (
              <button
                key={size.name}
                type="button"
                onClick={() => {
                  if (size.value) {
                    editor.chain().focus().setMark("textStyle", { fontSize: size.value }).run();
                  } else {
                    editor.chain().focus().unsetMark("textStyle").run();
                  }
                  setShowFontSizePicker(false);
                }}
                className="block w-full text-left px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded"
                style={{ fontSize: size.value || undefined }}
              >
                {size.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="w-px h-6 bg-gray-300 mx-1" />

      {/* Clear formatting */}
      <button
        type="button"
        onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()}
        className="px-2 py-1 rounded text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
        title="Clear formatting"
      >
        Clear
      </button>
    </div>
  );
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = "Enter text...",
  className = "",
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable features we don't need
        heading: false,
        bulletList: false,
        orderedList: false,
        blockquote: false,
        codeBlock: false,
        code: false,
        horizontalRule: false,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: "text-trig-green-600 hover:underline",
          target: "_blank",
          rel: "noopener noreferrer",
        },
      }),
      TextStyle,
      Color,
      FontSize,
    ],
    content: value,
    editorProps: {
      attributes: {
        class:
          "prose prose-sm max-w-none p-3 min-h-[100px] focus:outline-none",
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      // Return empty string if editor only contains empty paragraph
      onChange(html === "<p></p>" ? "" : html);
    },
  });

  // Update editor content when value prop changes externally
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || "");
    }
  }, [editor, value]);

  // Close colour picker when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      // This will be handled by the colour picker's own state
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  return (
    <div
      className={`relative border border-gray-300 rounded-md bg-white ${className}`}
    >
      <MenuBar editor={editor} />
      <EditorContent editor={editor} />
      {!value && (
        <div className="absolute top-[52px] left-3 text-gray-400 pointer-events-none">
          {placeholder}
        </div>
      )}
    </div>
  );
}

