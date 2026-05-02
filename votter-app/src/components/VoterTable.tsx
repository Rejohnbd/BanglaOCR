'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { VoterData } from '@/types';

interface VoterTableProps {
  voters: VoterData[];
}

export function VoterTable({ voters }: VoterTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const filteredVoters = voters.filter(
    (voter) =>
      voter.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      voter.voter_no?.includes(searchTerm) ||
      (voter.sl && voter.sl.includes(searchTerm))
  );

  // Pagination
  const totalPages = Math.ceil(filteredVoters.length / itemsPerPage);
  const paginatedVoters = filteredVoters.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const getCellClassName = (fieldStatus: boolean) => {
    return fieldStatus
      ? 'bg-green-50 dark:bg-green-900/20'
      : 'bg-red-50 dark:bg-red-900/20 font-semibold';
  };

  return (
    <Card variant="glass" className="w-full overflow-hidden">
      {/* Header with title and search */}
      <div className="flex flex-wrap justify-between items-center gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h3 className="text-lg font-semibold">Extracted Voters</h3>
          <p className="text-xs text-zinc-500 mt-0.5">
            {voters.length} total records • {filteredVoters.length} shown after
            filter
          </p>
        </div>

        <div className="relative">
          <input
            type="text"
            placeholder="Search by name, SL or voter ID..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="pl-10 pr-4 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-xl bg-white dark:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
          />
          <svg
            className="absolute left-3 top-2.5 w-4 h-4 text-zinc-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto mt-4">
        <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-700">
          <thead className="bg-zinc-50 dark:bg-zinc-800/50 sticky top-0">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                SL
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Voter No
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Father
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Mother
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Occupation
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                DOB (Bangla)
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                DOB (English)
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Address
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Source
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-700">
            {paginatedVoters.map((voter, idx) => (
              <tr
                key={idx}
                className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
              >
                <td
                  className={cn(
                    'px-4 py-3 text-sm',
                    getCellClassName(voter.fields?.sl || false)
                  )}
                >
                  {voter.sl || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm font-medium',
                    getCellClassName(voter.fields?.name || false)
                  )}
                >
                  {voter.name || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm font-mono',
                    getCellClassName(voter.fields?.voter_no || false)
                  )}
                >
                  {voter.voter_no || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm',
                    getCellClassName(voter.fields?.father_name || false)
                  )}
                >
                  {voter.father_name || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm',
                    getCellClassName(voter.fields?.mother_name || false)
                  )}
                >
                  {voter.mother_name || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm',
                    getCellClassName(voter.fields?.occupation || false)
                  )}
                >
                  {voter.occupation || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm font-mono',
                    getCellClassName(
                      voter.fields?.date_of_birth_bangla || false
                    )
                  )}
                >
                  {voter.date_of_birth_bangla || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm font-mono',
                    getCellClassName(voter.fields?.date_of_birth_eng || false)
                  )}
                >
                  {voter.date_of_birth_eng || '-'}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 text-sm max-w-xs truncate',
                    getCellClassName(voter.fields?.address || false)
                  )}
                >
                  <span title={voter.address || ''}>
                    {voter.address
                      ? voter.address.length > 40
                        ? voter.address.substring(0, 40) + '...'
                        : voter.address
                      : '-'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  {voter.status ? (
                    <Badge variant="success">Complete</Badge>
                  ) : (
                    <Badge variant="warning">Partial</Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-zinc-500">
                  <span className="text-xs font-mono bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded">
                    P{voter._source_page}:C{voter._source_cell}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <p className="text-sm text-zinc-500">
            Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
            {Math.min(currentPage * itemsPerPage, filteredVoters.length)} of{' '}
            {filteredVoters.length}
          </p>
          <div className="flex gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 disabled:opacity-50 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
            >
              Previous
            </button>
            <span className="px-4 py-1.5 text-sm bg-zinc-100 dark:bg-zinc-800 rounded-lg">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 disabled:opacity-50 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}

// Helper function for className merging
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}
