import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SelectedVideo } from "../components/SelectedVideo";

globalThis.URL.createObjectURL = vi.fn(() => "blob:mock");
globalThis.URL.revokeObjectURL = vi.fn();

function makeFile(name = "match.mp4") {
  return new File([new ArrayBuffer(0)], name, { type: "video/mp4" });
}

describe("SelectedVideo", () => {
  it("renders the file name", () => {
    render(
      <SelectedVideo
        file={makeFile("rally-game.mp4")}
        onAnalyze={vi.fn()}
        onReset={vi.fn()}
        analyzing={false}
      />
    );
    expect(screen.getByText(/rally-game\.mp4/)).toBeInTheDocument();
  });

  it("calls onAnalyze when Analyze video button is clicked", async () => {
    const onAnalyze = vi.fn();
    render(
      <SelectedVideo
        file={makeFile()}
        onAnalyze={onAnalyze}
        onReset={vi.fn()}
        analyzing={false}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /analyze video/i }));
    expect(onAnalyze).toHaveBeenCalledOnce();
  });

  it("calls onReset when Choose a different video is clicked", async () => {
    const onReset = vi.fn();
    render(
      <SelectedVideo
        file={makeFile()}
        onAnalyze={vi.fn()}
        onReset={onReset}
        analyzing={false}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /choose a different video/i }));
    expect(onReset).toHaveBeenCalledOnce();
  });

  it("disables Analyze button and shows busy text when analyzing=true", () => {
    render(
      <SelectedVideo
        file={makeFile()}
        onAnalyze={vi.fn()}
        onReset={vi.fn()}
        analyzing={true}
      />
    );
    const btn = screen.getByRole("button", { name: /uploading/i });
    expect(btn).toBeDisabled();
  });
});
