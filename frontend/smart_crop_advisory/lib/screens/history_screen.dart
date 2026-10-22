import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/daily_task.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';

enum _TaskFilter { all, completed, pending }

class HistoryScreen extends StatefulWidget {
  final AuthController auth;
  const HistoryScreen({super.key, required this.auth});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<_HistoryData> _future;
  _TaskFilter _filter = _TaskFilter.all;
  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_HistoryData> _load() async {
    final result = await Future.wait([
      widget.auth.loadTaskHistory(),
      widget.auth.loadCropCycles(),
      widget.auth.loadObservations(),
    ]);
    return _HistoryData(
      result[0] as List<DailyTask>,
      result[1] as List<CropCycle>,
      result[2] as List<Map<String, dynamic>>,
    );
  }

  Future<void> _refresh() async {
    final future = _load();
    setState(() => _future = future);
    await future;
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<_HistoryData>(
    future: _future,
    builder: (context, snap) {
      final data = snap.data;
      final visibleTasks =
          data?.tasks
              .where(
                (t) =>
                    _filter == _TaskFilter.all ||
                    t.status.toLowerCase() == _filter.name,
              )
              .toList() ??
          <DailyTask>[];
      visibleTasks.sort((a, b) => b.taskDate.compareTo(a.taskDate));
      return RefreshIndicator(
        onRefresh: () async => _refresh(),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Activity History',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text('Review your past crop activities.'),
            const SizedBox(height: 18),
            if (snap.connectionState == ConnectionState.waiting && data == null)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(35),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (snap.hasError && data == null)
              _HistoryMessage(
                title: 'Could not load activity history',
                message: snap.error is ApiException
                    ? (snap.error as ApiException).message
                    : 'Check your connection and try again.',
                action: _refresh,
              )
            else if (data != null) ...[
              Row(
                children: [
                  Expanded(
                    child: _Summary(
                      label: 'All tasks',
                      count: data.tasks.length,
                      color: AppColors.primary,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _Summary(
                      label: 'Completed',
                      count: data.tasks
                          .where((t) => t.status == 'completed')
                          .length,
                      color: AppColors.good,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _Summary(
                      label: 'Pending',
                      count: data.tasks
                          .where((t) => t.status == 'pending')
                          .length,
                      color: AppColors.warning,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Crop Observations',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              if (data.observations.isEmpty)
                const _HistoryMessage(
                  title: 'No crop observations yet',
                  message:
                      'Saved weather-risk assessments and symptom answers will appear here.',
                )
              else
                ...data.observations.map((observation) {
                  final note = observation['note']?.toString() ?? '';
                  final createdAt = observation['created_at']?.toString() ?? '';
                  final cycleId = observation['crop_cycle_id'];

                  final crop = data.cycles
                      .where(
                        (cycle) => cycle.id.toString() == cycleId.toString(),
                      )
                      .firstOrNull;

                  return Card(
                    child: ListTile(
                      leading: const Icon(
                        Icons.eco_outlined,
                        color: AppColors.primary,
                      ),
                      title: Text(crop?.cropName ?? 'Crop observation'),
                      subtitle: Text(
                        [if (createdAt.isNotEmpty) createdAt, note].join('\n'),
                      ),
                      isThreeLine: true,
                    ),
                  );
                }),
              const SizedBox(height: 20),
              const SizedBox(height: 18),
              Wrap(
                spacing: 8,
                children: [
                  for (final filter in _TaskFilter.values)
                    ChoiceChip(
                      label: Text(switch (filter) {
                        _TaskFilter.all => 'All',
                        _TaskFilter.completed => 'Completed',
                        _TaskFilter.pending => 'Pending',
                      }),
                      selected: _filter == filter,
                      onSelected: (_) => setState(() => _filter = filter),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              if (data.tasks.isEmpty)
                const _HistoryMessage(
                  title: 'No activity history yet',
                  message:
                      'Completed and previous farming activities will appear here when available.',
                )
              else
                ...visibleTasks.map((task) {
                  final crop = data.cycles
                      .where((c) => c.id == task.cropCycleId)
                      .firstOrNull;
                  final done = task.status == 'completed';
                  return Card(
                    child: ListTile(
                      leading: Icon(
                        done
                            ? Icons.check_circle_outline
                            : Icons.pending_outlined,
                        color: done ? AppColors.good : AppColors.warning,
                      ),
                      title: Text(task.title),
                      subtitle: Text(
                        '${crop?.cropName ?? 'Crop'} · ${_historyDate(task.taskDate)}${task.description?.isNotEmpty == true ? '\n${task.description}' : ''}',
                      ),
                      isThreeLine: task.description?.isNotEmpty == true,
                      trailing: Chip(
                        label: Text(done ? 'Completed' : task.status),
                      ),
                    ),
                  );
                }),
              if (data.tasks.isNotEmpty && visibleTasks.isEmpty)
                const _HistoryMessage(
                  title: 'No matching activities',
                  message: 'Choose another filter to see available tasks.',
                ),
            ],
          ],
        ),
      );
    },
  );
}

class _HistoryData {
  final List<DailyTask> tasks;
  final List<CropCycle> cycles;
  final List<Map<String, dynamic>> observations;

  const _HistoryData(this.tasks, this.cycles, this.observations);
}

class _Summary extends StatelessWidget {
  final String label;
  final int count;
  final Color color;
  const _Summary({
    required this.label,
    required this.count,
    required this.color,
  });
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          Text(
            '$count',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    ),
  );
}

class _HistoryMessage extends StatelessWidget {
  final String title, message;
  final VoidCallback? action;
  const _HistoryMessage({
    required this.title,
    required this.message,
    this.action,
  });
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(message),
          if (action != null)
            TextButton(onPressed: action, child: const Text('Retry')),
        ],
      ),
    ),
  );
}

String _historyDate(DateTime d) => '${d.day}/${d.month}/${d.year}';
