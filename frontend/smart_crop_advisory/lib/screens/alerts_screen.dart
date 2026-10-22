import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/daily_task.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';

class AlertsScreen extends StatefulWidget {
  final AuthController auth;
  const AlertsScreen({super.key, required this.auth});
  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  late Future<({List<DailyTask> tasks, List<CropCycle> cycles})> _future;
  final Set<int> _toggling = {};

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<({List<DailyTask> tasks, List<CropCycle> cycles})> _load() async {
    final values = await Future.wait([
      widget.auth.loadUpcomingTasks(),
      widget.auth.loadCropCycles(),
    ]);
    return (
      tasks: values[0] as List<DailyTask>,
      cycles: values[1] as List<CropCycle>,
    );
  }

  Future<void> _toggleTask(DailyTask task) async {
    if (_toggling.contains(task.id)) return;
    setState(() => _toggling.add(task.id));

    try {
      if (task.status.toLowerCase() == 'completed') {
        await widget.auth.reopenTask(task.id);
      } else {
        await widget.auth.completeTask(task.id);
      }
      if (mounted) setState(() => _future = _load());
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error is ApiException ? error.message : 'Could not update task.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _toggling.remove(task.id));
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: () async => setState(() => _future = _load()),
    child: FutureBuilder<({List<DailyTask> tasks, List<CropCycle> cycles})>(
      future: _future,
      builder: (context, snapshot) {
        final data = snapshot.data;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Crop Alerts',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text('Upcoming activities from your crop schedule.'),
            const SizedBox(height: 20),
            if (snapshot.connectionState == ConnectionState.waiting &&
                data == null)
              const Center(child: CircularProgressIndicator())
            else if (snapshot.hasError && data == null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Text(
                    snapshot.error is ApiException
                        ? (snapshot.error as ApiException).message
                        : 'Upcoming activities are unavailable. Pull down to retry.',
                  ),
                ),
              )
            else if (data != null && data.tasks.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'No upcoming tasks are available. Daily monitoring can be generated from Advisory.',
                  ),
                ),
              )
            else if (data != null)
              ...data.tasks.map((task) {
                final crop = data.cycles
                    .where((cycle) => cycle.id == task.cropCycleId)
                    .firstOrNull;
                final isFertilizerAlert =
                    task.sourceRuleType == 'fertilizer_review';
                final isCompleted = task.status.toLowerCase() == 'completed';
                final isToggling = _toggling.contains(task.id);
                return Card(
                  child: ListTile(
                    leading: Icon(
                      isFertilizerAlert
                          ? Icons.eco_outlined
                          : Icons.notifications_none,
                      color: AppColors.primary,
                    ),
                    title: Text(task.title),
                    subtitle: Text(
                      '${crop?.cropName ?? 'Crop'} · ${task.taskDate.day}/${task.taskDate.month}/${task.taskDate.year}\n${task.description ?? ''}',
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Chip(
                          label: Text(
                            isFertilizerAlert ? 'Review Schedule' : task.status,
                          ),
                        ),
                        Checkbox(
                          value: isCompleted,
                          onChanged: isToggling
                              ? null
                              : (_) => _toggleTask(task),
                        ),
                      ],
                    ),
                    isThreeLine: task.description?.isNotEmpty == true,
                  ),
                );
              }),
          ],
        );
      },
    ),
  );
}
