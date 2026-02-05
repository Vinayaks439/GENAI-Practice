import torch

"""
Data Type PyTorch Equivalent
32-bit floating point torch.float32 or torch.float
64-bit floating point torch.float64 or torch.double
16-bit floating point torch.float16 or torch.half
8-bit integer (unsigned) torch.uint8
8-bit integer (signed) torch.int8
16-bit integer (signed) torch.int16 or torch.short
32-bit integer (signed) torch.int32 or torch.int
64-bit integer (signed) torch.int64 or torch.long
Boolean torch.bool
"""
ten = torch.tensor([[1,2,3],[2,4,5]])
floattorch = torch.tensor([0.1,0.2,0.3], dtype=torch.float32)
print(ten)  
print(ten.shape)
print(floattorch)
print(floattorch.shape)

#Rand

r = torch.rand(2,2,2)
print(r)
print(r.shape)

#zeros

zeros = torch.zeros(2,2,3)
print(zeros)
print(zeros.shape)

#ones

ones = torch.ones(2,2,3)
print(ones)
print(ones.shape)


#Creating an Identity Matix Tensor

eye = torch.eye(5)
print(eye)
print(eye.shape)

# Munging Operations

a = torch.tensor([[1,2],[3,4]])

print(a[0][0]) # Accessing element at first row and first column

# Reshaping a Tensor

b = torch.tensor([[1,2,3,4],[5,6,7,8]])
reshaped_b = b.view(4,2)  # Reshape to 4 rows and 2 columns
print(reshaped_b)

#Concatenating Two Tensors
c1 = torch.tensor([[1,2],[3,4]])
c2 = torch.tensor([[5,6],[7,8]])
concatenated_c = torch.cat((c1, c2), dim=0)  # Concatenate along rows
print(concatenated_c)

# Stacking Tensors

d1 = torch.tensor([1,2,3])
d2 = torch.tensor([4,5,6])
stacked_d = torch.stack((d1, d2), dim=0)  # Stack along a new dimension
print(stacked_d)