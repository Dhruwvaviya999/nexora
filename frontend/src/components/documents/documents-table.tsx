"use client";

import * as React from "react";
import { Download, FileText, MoreHorizontal, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { useDeleteDocument } from "@/hooks/use-documents";
import { getErrorMessage } from "@/lib/api/errors";
import { formatBytes, formatDate } from "@/lib/format";
import type { DocumentItem } from "@/types/document";

export function DocumentsTable({ documents }: { documents: DocumentItem[] }) {
  const deleteDocument = useDeleteDocument();
  const [target, setTarget] = React.useState<DocumentItem | null>(null);

  async function onDelete() {
    if (!target) return;
    try {
      await deleteDocument.mutateAsync(target.id);
      toast.success("Document deleted");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead className="hidden sm:table-cell">Type</TableHead>
            <TableHead className="hidden md:table-cell">Size</TableHead>
            <TableHead className="hidden lg:table-cell">Uploaded</TableHead>
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell>
                <div className="flex items-center gap-2">
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <span className="font-medium">{doc.title}</span>
                </div>
              </TableCell>
              <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                {doc.file_type || "—"}
              </TableCell>
              <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                {formatBytes(doc.file_size)}
              </TableCell>
              <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                {formatDate(doc.created_at)}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="size-8">
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {doc.file_url && (
                      <DropdownMenuItem asChild>
                        <a href={doc.file_url} target="_blank" rel="noreferrer" download>
                          <Download className="size-4" />
                          Download
                        </a>
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      variant="destructive"
                      onClick={() => setTarget(doc)}
                    >
                      <Trash2 className="size-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={!!target}
        onOpenChange={(o) => !o && setTarget(null)}
        title="Delete document?"
        description={target ? `"${target.title}" will be permanently removed.` : ""}
        onConfirm={onDelete}
      />
    </div>
  );
}
