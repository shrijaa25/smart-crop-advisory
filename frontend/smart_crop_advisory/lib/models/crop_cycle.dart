class CropCycle {
  final int id;
  final int farmId;
  final String cropName;
  final String? variety;
  final DateTime plantingDate;
  final String plantingMethod;
  final double? areaValue;
  final String areaUnit;
  final String status;
  final String? notes;

  const CropCycle({
    required this.id,
    required this.farmId,
    required this.cropName,
    required this.variety,
    required this.plantingDate,
    required this.plantingMethod,
    required this.areaValue,
    required this.areaUnit,
    required this.status,
    required this.notes,
  });

  factory CropCycle.fromJson(Map<String, dynamic> json) => CropCycle(
    id: (json['id'] as num).toInt(),
    farmId: (json['farm_id'] as num).toInt(),
    cropName: json['crop_name'] as String,
    variety: json['variety'] as String?,
    plantingDate: DateTime.parse(json['planting_date'] as String),
    plantingMethod: json['planting_method'] as String? ?? 'transplanting',
    areaValue: (json['area_value'] as num?)?.toDouble(),
    areaUnit: json['area_unit'] as String? ?? 'acre',
    status: json['status'] as String? ?? 'active',
    notes: json['notes'] as String?,
  );
}
