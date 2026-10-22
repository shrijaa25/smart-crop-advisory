import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/daily_task.dart';
import '../models/farm.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import 'crop_registration_screen.dart';

class AdvisoryScreen extends StatefulWidget {
  final AuthController auth;
  const AdvisoryScreen({super.key, required this.auth});

  @override
  State<AdvisoryScreen> createState() => _AdvisoryScreenState();
}

class _AdvisoryScreenState extends State<AdvisoryScreen> {
  late Future<_AdvisoryData> _future;
  int? _cropId;
  int? _updatingTask;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_AdvisoryData> _load({bool generate = true}) async {
    final result = await Future.wait([
      widget.auth.loadFarms(),
      widget.auth.loadCropCycles(),
    ]);
    final cycles = result[1] as List<CropCycle>;
    final active = cycles.where((c) => c.status == 'active').toList();
    final selected =
        active.where((c) => c.id == _cropId).firstOrNull ?? active.firstOrNull;
    Map<String, dynamic>? stage;
    Map<String, dynamic> weather = {
      'status': 'unavailable',
      'reason': 'Weather is unavailable.',
    };
    if (selected != null) {
      _cropId = selected.id;
      try {
        stage = await widget.auth.loadCropStage(selected.id, DateTime.now());
      } catch (_) {
        // Crop details remain useful when the stage endpoint has no match.
      }
      final farms = result[0] as List<Farm>;
      final farm = farms.where((f) => f.id == selected.farmId).firstOrNull;

      final town = [
        farm?.village,
        farm?.district,
        farm?.state,
      ].whereType<String>().map((value) => value.trim()).firstWhere(
        (value) => value.isNotEmpty,
        orElse: () => '',
      );

      try {
        if (town.isNotEmpty) {
          weather = await widget.auth.loadWeather(town);
        } else {
          weather = {
            'status': 'unavailable',
            'reason':
                'Add a village or district to your farm details to load weather.',
          };
        }
      } catch (_) {
        weather = {
          'status': 'unavailable',
          'reason': 'Weather service is unavailable.',
        };
      }
    }
    if (generate) {
      try {
        await widget.auth.generateTasks(DateTime.now());
      } catch (_) {
        // Keep existing tasks visible when generation or weather is unavailable.
      }
    }
    List<DailyTask> tasks = const [];
    try {
      tasks = await widget.auth.loadTasksForToday();
    } catch (_) {
      // The rest of the crop profile remains useful if tasks cannot load.
    }
    return _AdvisoryData(
      farms: result[0] as List<Farm>,
      cycles: active,
      tasks: tasks,
      stage: stage,
      weather: weather,
    );
  }

  void _refresh() => setState(() => _future = _load());

  Future<void> _addCrop() async {
    await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => CropRegistrationScreen(auth: widget.auth),
      ),
    );
    if (mounted) _refresh();
  }

  Future<void> _toggle(DailyTask task) async {
    if (_updatingTask != null) return;
    setState(() => _updatingTask = task.id);
    try {
      if (task.status.toLowerCase() == 'completed') {
        await widget.auth.reopenTask(task.id);
      } else {
        await widget.auth.completeTask(task.id);
      }
      if (mounted) _refresh();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error is ApiException
                  ? error.message
                  : 'Could not update the task. Try again.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _updatingTask = null);
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<_AdvisoryData>(
    future: _future,
    builder: (context, snapshot) {
      final data = snapshot.data;
      final name = widget.auth.profile?.fullName.trim();
      return RefreshIndicator(
        onRefresh: () async => _refresh(),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          children: [
            Text(
              _greeting(),
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 4),
            Text(
              name?.isNotEmpty == true ? name! : 'Your daily crop guidance',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 4),
            Text(
              _dateLabel(DateTime.now()),
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 22),
            if (snapshot.connectionState == ConnectionState.waiting &&
                data == null)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(36),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (snapshot.hasError && data == null)
              _MessageCard(
                title: 'Could not load your advisory',
                message: snapshot.error is ApiException
                    ? (snapshot.error as ApiException).message
                    : 'Check your connection and try again.',
                action: 'Retry',
                onAction: _refresh,
              )
            else if (data != null) ...[
              _sectionTitle('Your crop'),
              const SizedBox(height: 10),
              if (data.cycles.isEmpty)
                _MessageCard(
                  title: 'Set up your first crop',
                  message:
                      'Add your crop details to receive guidance based on your farming schedule.',
                  action: 'Add Crop',
                  onAction: _addCrop,
                )
              else ...[
                if (data.cycles.length > 1)
                  DropdownButtonFormField<int>(
                    initialValue: _cropId,
                    decoration: const InputDecoration(
                      labelText: 'Selected crop',
                      border: OutlineInputBorder(),
                    ),
                    items: data.cycles
                        .map(
                          (c) => DropdownMenuItem(
                            value: c.id,
                            child: Text(_cropLabel(c)),
                          ),
                        )
                        .toList(),
                    onChanged: (id) {
                      if (id != null) {
                        setState(() {
                          _cropId = id;
                          _future = _load(generate: false);
                        });
                      }
                    },
                  ),
                const SizedBox(height: 10),
                _CropCard(
                  cycle: data.cycles.firstWhere(
                    (c) => c.id == _cropId,
                    orElse: () => data.cycles.first,
                  ),
                  farms: data.farms,
                  stage: data.stage,
                ),
                const SizedBox(height: 12),
                _WeatherCard(weather: data.weather),
              ],
              const SizedBox(height: 24),
              _sectionTitle('Today’s tasks'),
              const SizedBox(height: 10),
              if (data.tasks.isEmpty)
                const _MessageCard(
                  title: 'No tasks due today',
                  message:
                      'Daily monitoring tasks are generated for active crops. Refresh or generate tasks if the list is empty.',
                )
              else
                ...data.tasks.map(
                  (task) => _TaskCard(
                    task: task,
                    cropName:
                        data.cycles
                            .where((cycle) => cycle.id == task.cropCycleId)
                            .firstOrNull
                            ?.cropName ??
                        'Crop',
                    busy: _updatingTask == task.id,
                    onToggle: () => _toggle(task),
                  ),
                ),
              const SizedBox(height: 24),
              _sectionTitle('Crop guidance'),
              const SizedBox(height: 10),
              _MessageCard(
                title: data.tasks.isEmpty
                    ? 'Crop guidance is not available for this stage yet.'
                    : 'Guidance from your tasks',
                message: data.tasks.isEmpty
                    ? 'Recommendations appear here when relevant farming information has been reviewed and verified.'
                    : 'The task list above contains the verified actions currently available for today.',
              ),
            ],
          ],
        ),
      );
    },
  );

  String _greeting() {
    final hour = DateTime.now().hour;
    return hour < 12
        ? 'Good morning'
        : hour < 17
        ? 'Good afternoon'
        : 'Good evening';
  }
}

class _AdvisoryData {
  final List<Farm> farms;
  final List<CropCycle> cycles;
  final List<DailyTask> tasks;
  final Map<String, dynamic>? stage;
  final Map<String, dynamic> weather;
  const _AdvisoryData({
    required this.farms,
    required this.cycles,
    required this.tasks,
    required this.stage,
    required this.weather,
  });
}

class _WeatherCard extends StatelessWidget {
  final Map<String, dynamic> weather;
  const _WeatherCard({required this.weather});

  @override
  Widget build(BuildContext context) {
    final status = weather['status'] as String? ?? 'unavailable';
    final current = weather['current'] as Map<String, dynamic>?;
    final forecast = weather['forecast'] as Map<String, dynamic>?;
    final details = <String>[];
    if (current?['temperature_2m'] != null) {
      details.add('Temperature ${current!['temperature_2m']}°C');
    }
    if (current?['precipitation'] != null) {
      details.add('Current precipitation ${current!['precipitation']} mm');
    }
    if (forecast?['precipitation_probability_max_percent'] != null) {
      details.add(
        'Forecast rain chance ${forecast!['precipitation_probability_max_percent']}%',
      );
    }
    final reason = weather['reason'] as String?;
    return Card(
      child: ListTile(
        leading: const Icon(Icons.cloud_outlined, color: AppColors.primary),
        title: Text('Weather · $status'),
        subtitle: Text(
          [
            ...details,
            ?reason,
            if (details.isEmpty && reason == null)
              'Weather details are unavailable.',
            'Weather provides context only; no action threshold is inferred.',
          ].join('\n'),
        ),
        isThreeLine: true,
      ),
    );
  }
}

class _CropCard extends StatelessWidget {
  final CropCycle cycle;
  final List<Farm> farms;
  final Map<String, dynamic>? stage;
  const _CropCard({
    required this.cycle,
    required this.farms,
    required this.stage,
  });

  @override
  Widget build(BuildContext context) {
    final farm = farms.where((f) => f.id == cycle.farmId).firstOrNull;
    final age = DateTime.now().difference(cycle.plantingDate).inDays;
    final stageName = stage?['stage_name'] as String?;
    final areaValue = cycle.areaValue ?? farm?.areaValue;
    final areaUnit = cycle.areaValue != null ? cycle.areaUnit : farm?.areaUnit;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const CircleAvatar(
                  backgroundColor: AppColors.primaryLight,
                  child: Icon(Icons.eco, color: AppColors.primary),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _cropLabel(cycle),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                if (cycle.status == 'active') const Chip(label: Text('Active')),
              ],
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 16,
              runSpacing: 10,
              children: [
                _Detail(
                  label: 'Planted',
                  value: _dateLabel(cycle.plantingDate),
                ),
                if (age >= 0) _Detail(label: 'Crop age', value: 'Day $age'),
                if (areaValue != null)
                  _Detail(
                    label: 'Area',
                    value: '$areaValue ${areaUnit ?? ''}'.trim(),
                  ),
                if (farm?.name case final farmName?)
                  _Detail(label: 'Farm', value: farmName),
                if (stageName != null)
                  _Detail(label: 'Growth stage', value: stageName),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Detail extends StatelessWidget {
  final String label, value;
  const _Detail({required this.label, required this.value});
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 140,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
        ),
        Text(
          value,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    ),
  );
}

class _TaskCard extends StatelessWidget {
  final DailyTask task;
  final String cropName;
  final bool busy;
  final VoidCallback onToggle;
  const _TaskCard({
    required this.task,
    required this.cropName,
    required this.busy,
    required this.onToggle,
  });
  @override
  Widget build(BuildContext context) {
    final done = task.status.toLowerCase() == 'completed';
    return Card(
      child: ListTile(
        leading: Icon(
          done ? Icons.check_circle : Icons.radio_button_unchecked,
          color: done ? AppColors.good : AppColors.warning,
        ),
        title: Text(task.title),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (task.description?.isNotEmpty == true) Text(task.description!),
            const SizedBox(height: 4),
            Text(
              '$cropName · ${_dateLabel(task.taskDate)} · ${task.status}${task.sourceRuleType == null ? '' : ' · ${task.sourceRuleType!.replaceAll('_', ' ')}'}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        trailing: busy
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : TextButton(
                onPressed: onToggle,
                child: Text(done ? 'Reopen' : 'Complete'),
              ),
        isThreeLine: task.description?.isNotEmpty == true,
      ),
    );
  }
}

class _MessageCard extends StatelessWidget {
  final String title, message;
  final String? action;
  final VoidCallback? onAction;
  const _MessageCard({
    required this.title,
    required this.message,
    this.action,
    this.onAction,
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
          if (action != null) ...[
            const SizedBox(height: 12),
            FilledButton.tonal(onPressed: onAction, child: Text(action!)),
          ],
        ],
      ),
    ),
  );
}

Widget _sectionTitle(String value) => Text(
  value,
  style: const TextStyle(
    fontSize: 19,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  ),
);
String _cropLabel(CropCycle cycle) =>
    '${cycle.cropName[0].toUpperCase()}${cycle.cropName.substring(1)}${cycle.variety?.isNotEmpty == true ? ' · ${cycle.variety}' : ''}';
String _dateLabel(DateTime date) => '${date.day}/${date.month}/${date.year}';
